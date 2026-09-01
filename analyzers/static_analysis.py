import ast
import re
from typing import List
from core.schemas import ReviewIssue


class PythonASTAnalyzer(ast.NodeVisitor):
    """AST Node Visitor to detect deterministic code quality and security issues in Python code."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.issues: List[ReviewIssue] = []

    def run(self) -> List[ReviewIssue]:
        self.issues.clear()
        
        # 1. Check for Syntax Errors first
        try:
            tree = ast.parse(self.code)
        except SyntaxError as syn_err:
            self.issues.append(
                ReviewIssue(
                    category="Syntax Error",
                    severity="CRITICAL",
                    line=syn_err.lineno or 1,
                    title="Python Syntax Error",
                    description=f"Syntax error: {syn_err.msg}",
                    impact="The code cannot be compiled or executed by Python interpreter.",
                    recommendation=f"Fix syntax at line {syn_err.lineno}: {syn_err.text or syn_err.msg}",
                    evidence=syn_err.text.strip() if syn_err.text else f"Line {syn_err.lineno}",
                    source="Deterministic (AST)"
                )
            )
            return self.issues

        # 2. Check for Hardcoded Secrets using Regex on lines
        self._check_hardcoded_secrets()

        # 3. Visit AST nodes
        self.visit(tree)

        return self.issues

    def _check_hardcoded_secrets(self):
        secret_patterns = [
            (r'(?i)(api[_-]?key|secret|token|password|auth_token)\s*=\s*["\']([A-Za-z0-9_\-]{8,})["\']', "Hardcoded API Key / Secret"),
            (r'AIzaSy[A-Za-z0-9_\-]{33}', "Google API Key Pattern"),
            (r'sk-[A-Za-z0-9]{32,}', "Secret Key Pattern"),
        ]
        for lineno, line in enumerate(self.lines, start=1):
            for pattern, title in secret_patterns:
                match = re.search(pattern, line)
                if match:
                    val = match.group(0)
                    if any(p in val.lower() for p in ["your_", "placeholder", "xxx", "example", "env"]):
                        continue
                    self.issues.append(
                        ReviewIssue(
                            category="Security Vulnerability",
                            severity="CRITICAL",
                            line=lineno,
                            title=title,
                            description="Hardcoded sensitive secret detected in source code.",
                            impact="Secrets committed to version control can lead to unauthorized system access.",
                            recommendation="Load sensitive secrets from environment variables using `os.getenv()` or `.env` file.",
                            evidence=line.strip(),
                            source="Deterministic (AST)"
                        )
                    )

    def visit_Call(self, node: ast.Call):
        # Detect eval() and exec()
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ("eval", "exec"):
                self.issues.append(
                    ReviewIssue(
                        category="Security Vulnerability",
                        severity="CRITICAL",
                        line=node.lineno,
                        title=f"Dangerous `{func_name}()` Usage",
                        description=f"Use of built-in `{func_name}()` allows arbitrary code execution.",
                        impact="Executing untrusted input via `eval`/`exec` grants remote code execution capabilities.",
                        recommendation=f"Avoid using `{func_name}()`. Use `ast.literal_eval()` or safer parsing alternatives.",
                        evidence=self._get_line_snippet(node.lineno),
                        source="Deterministic (AST)"
                    )
                )

        # Detect subprocess shell=True
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in ("Popen", "run", "call", "check_output"):
                for keyword in node.keywords:
                    if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                        self.issues.append(
                            ReviewIssue(
                                category="Security Vulnerability",
                                severity="HIGH",
                                line=node.lineno,
                                title="Unsafe Subprocess with `shell=True`",
                                description="Passing `shell=True` to subprocess functions enables shell injection vulnerabilities.",
                                impact="Command injection if arguments contain unsanitized user input.",
                                recommendation="Pass argument lists to subprocess without `shell=True` (e.g. `subprocess.run(['ls', '-l'])`).",
                                evidence=self._get_line_snippet(node.lineno),
                                source="Deterministic (AST)"
                            )
                        )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Detect bare except:
        if node.type is None:
            self.issues.append(
                ReviewIssue(
                    category="Code Quality",
                    severity="MEDIUM",
                    line=node.lineno,
                    title="Bare `except:` Catch-All Clause",
                    description="Catching all exceptions with a bare `except:` handles KeyboardInterrupt, SystemExit, and masks critical errors.",
                    impact="Makes debugging extremely difficult and prevents graceful program shutdown.",
                    recommendation="Catch specific exceptions such as `except Exception:` or `except ValueError:`.",
                    evidence=self._get_line_snippet(node.lineno),
                    source="Deterministic (AST)"
                )
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        guarded_vars = set()
        for stmt in node.body:
            if isinstance(stmt, ast.If):
                for sub in ast.walk(stmt.test):
                    if isinstance(sub, ast.Name):
                        guarded_vars.add(sub.id)
        
        old_guarded = getattr(self, "_current_guarded_vars", set())
        self._current_guarded_vars = old_guarded | guarded_vars
        self.generic_visit(node)
        self._current_guarded_vars = old_guarded

    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.issues.append(
                    ReviewIssue(
                        category="Logic Bug",
                        severity="HIGH",
                        line=node.lineno,
                        title="Division or Modulo by Zero",
                        description="Literal division or modulo operation by zero detected.",
                        impact="Triggers unhandled `ZeroDivisionError` exception at runtime.",
                        recommendation="Check the denominator before performing division.",
                        evidence=self._get_line_snippet(node.lineno),
                        source="Deterministic (AST)"
                    )
                )
            elif isinstance(node.right, (ast.Name, ast.Call)):
                denom_var = node.right.id if isinstance(node.right, ast.Name) else (
                    node.right.args[0].id if (isinstance(node.right, ast.Call) and node.right.args and isinstance(node.right.args[0], ast.Name)) else None
                )
                denom_name = node.right.id if isinstance(node.right, ast.Name) else (
                    f"{node.right.func.id}(...)" if isinstance(node.right.func, ast.Name) else "expression"
                )
                
                current_guarded = getattr(self, "_current_guarded_vars", set())
                if not denom_var or denom_var not in current_guarded:
                    self.issues.append(
                        ReviewIssue(
                            category="Logic Bug",
                            severity="MEDIUM",
                            line=node.lineno,
                            title=f"Potential Division by Zero (`{denom_name}`)",
                            description=f"Division operation by denominator `{denom_name}` without zero validation.",
                            impact=f"If `{denom_name}` evaluates to 0, a `ZeroDivisionError` will be raised at runtime.",
                            recommendation=f"Validate denominator before dividing: check that `{denom_name}` is non-zero.",
                            evidence=self._get_line_snippet(node.lineno),
                            source="Deterministic (AST)"
                        )
                    )
        self.generic_visit(node)

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""


class CppStaticAnalyzer:
    """Deterministic Static Analyzer for C++ source code."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.issues: List[ReviewIssue] = []

    def run(self) -> List[ReviewIssue]:
        self.issues.clear()
        
        # 1. Check basic delimiter syntax balance
        self._check_delimiters()
        
        # 2. Check hardcoded secrets
        self._check_secrets()

        # 3. Line-by-line static patterns
        for lineno, line in enumerate(self.lines, start=1):
            clean_line = line.strip()
            # Skip pure comments
            if clean_line.startswith("//") or clean_line.startswith("/*"):
                continue

            # Unsafe buffer functions
            if re.search(r'\b(gets|strcpy|strcat|sprintf)\s*\(', clean_line):
                match_func = re.search(r'\b(gets|strcpy|strcat|sprintf)\b', clean_line).group(1)
                self.issues.append(
                    ReviewIssue(
                        category="Security Vulnerability",
                        severity="CRITICAL",
                        line=lineno,
                        title=f"Unsafe C Function `{match_func}()` (Buffer Overflow Risk)",
                        description=f"`{match_func}()` does not perform bounds checking, leading to buffer overflow vulnerabilities.",
                        impact="Attackers can overwrite adjacent stack memory to execute arbitrary shellcode.",
                        recommendation=f"Replace `{match_func}()` with safe modern alternatives like `std::string`, `strncpy_s()`, or `snprintf()`.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

            # Command injection via system() / popen()
            if re.search(r'\b(system|popen)\s*\(', clean_line):
                self.issues.append(
                    ReviewIssue(
                        category="Security Vulnerability",
                        severity="HIGH",
                        line=lineno,
                        title="Command Execution via `system()` / `popen()`",
                        description="Direct invocation of the system shell can allow arbitrary command injection.",
                        impact="Unsanitized input passed into system commands allows arbitrary system manipulation.",
                        recommendation="Avoid `system()`. Use parameterized process execution APIs (e.g. `execve` / `CreateProcess`) with strict argument lists.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

            # Division by zero
            if re.search(r'/\s*0\b', clean_line):
                self.issues.append(
                    ReviewIssue(
                        category="Logic Bug",
                        severity="HIGH",
                        line=lineno,
                        title="Division by Zero",
                        description="Literal division by zero detected in expression.",
                        impact="Causes undefined behavior or immediate program crash (`SIGFPE`).",
                        recommendation="Check the divisor before dividing to ensure it is non-zero.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

            # Memory leak: raw new[] without delete or malloc
            if re.search(r'\b(new\s+\w+(\s*\[\s*[^\]]+\s*\]|\s*\([^)]*\)))\b', clean_line) and "std::unique_ptr" not in clean_line and "std::shared_ptr" not in clean_line:
                if "delete" not in self.code:
                    self.issues.append(
                        ReviewIssue(
                            category="Code Quality",
                            severity="MEDIUM",
                            line=lineno,
                            title="Potential Memory Leak (Raw `new` without `delete`)",
                            description="Raw pointer dynamic allocation detected without corresponding deallocation in code scope.",
                            impact="Causes progressive heap memory exhaustion in long-running processes.",
                            recommendation="Use modern RAII smart pointers (`std::unique_ptr`, `std::make_unique`) or `std::vector` instead of raw `new`.",
                            evidence=clean_line,
                            source="Deterministic (AST)"
                        )
                    )

            # Catch-all catch (...)
            if re.search(r'catch\s*\(\s*\.\.\.\s*\)', clean_line):
                self.issues.append(
                    ReviewIssue(
                        category="Code Quality",
                        severity="MEDIUM",
                        line=lineno,
                        title="Bare `catch (...)` Catch-All Clause",
                        description="Catching all exceptions with `catch (...)` hides the exception type and prevents diagnostic logging.",
                        impact="Suppresses unexpected system aborts and masks critical internal faults.",
                        recommendation="Catch specific `const std::exception&` types or re-throw unexpected errors.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

        return self.issues

    def _check_delimiters(self):
        stack = []
        mapping = {')': '(', '}': '{', ']': '['}
        for lineno, line in enumerate(self.lines, start=1):
            for char in line:
                if char in "({[":
                    stack.append((char, lineno))
                elif char in ")}]":
                    if not stack or stack[-1][0] != mapping[char]:
                        self.issues.append(
                            ReviewIssue(
                                category="Syntax Error",
                                severity="CRITICAL",
                                line=lineno,
                                title="Mismatched / Unclosed Bracket",
                                description=f"Unmatched closing delimiter `{char}` found.",
                                impact="C++ code will fail to compile.",
                                recommendation=f"Ensure opening and closing delimiters match properly.",
                                evidence=line.strip(),
                                source="Deterministic (AST)"
                            )
                        )
                        return
                    stack.pop()
        if stack:
            unclosed, lineno = stack[0]
            self.issues.append(
                ReviewIssue(
                    category="Syntax Error",
                    severity="CRITICAL",
                    line=lineno,
                    title="Unclosed Delimiter in C++",
                    description=f"Opening delimiter `{unclosed}` at line {lineno} is never closed.",
                    impact="C++ compiler will fail with syntax compilation error.",
                    recommendation="Add the matching closing delimiter.",
                    evidence=self.lines[lineno - 1].strip() if lineno <= len(self.lines) else "",
                    source="Deterministic (Static)"
                )
            )

    def _check_secrets(self):
        secret_patterns = [
            (r'(?i)(api[_-]?key|secret|token|password|auth_token)\s*=\s*["\']([A-Za-z0-9_\-]{8,})["\']', "Hardcoded API Key / Secret"),
            (r'AIzaSy[A-Za-z0-9_\-]{33}', "Google API Key Pattern"),
            (r'sk-[A-Za-z0-9]{32,}', "Secret Key Pattern"),
        ]
        for lineno, line in enumerate(self.lines, start=1):
            for pattern, title in secret_patterns:
                match = re.search(pattern, line)
                if match:
                    val = match.group(0)
                    if any(p in val.lower() for p in ["your_", "placeholder", "xxx", "example", "env"]):
                        continue
                    self.issues.append(
                        ReviewIssue(
                            category="Security Vulnerability",
                            severity="CRITICAL",
                            line=lineno,
                            title=title,
                            description="Hardcoded sensitive secret detected in C++ source code.",
                            impact="Committing plaintext credentials allows unauthorized access to production APIs.",
                            recommendation="Load secrets from environment variables using `std::getenv()` or a secure configuration file.",
                            evidence=line.strip(),
                            source="Deterministic (AST)"
                        )
                    )


class JavaStaticAnalyzer:
    """Deterministic Static Analyzer for Java source code."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.issues: List[ReviewIssue] = []

    def run(self) -> List[ReviewIssue]:
        self.issues.clear()
        
        # 1. Check basic delimiter syntax balance
        self._check_delimiters()
        
        # 2. Check hardcoded secrets
        self._check_secrets()

        # 3. Line-by-line static patterns
        for lineno, line in enumerate(self.lines, start=1):
            clean_line = line.strip()
            if clean_line.startswith("//") or clean_line.startswith("/*"):
                continue

            # Command injection: Runtime.getRuntime().exec / ProcessBuilder
            if re.search(r'(Runtime\.getRuntime\(\)\.exec|new\s+ProcessBuilder)\s*\(', clean_line):
                self.issues.append(
                    ReviewIssue(
                        category="Security Vulnerability",
                        severity="HIGH",
                        line=lineno,
                        title="Unsafe Process Execution in Java (`Runtime.exec`)",
                        description="Invoking OS commands with `Runtime.getRuntime().exec` can lead to command injection.",
                        impact="If unsanitized input is passed into command strings, attackers can execute arbitrary OS commands.",
                        recommendation="Use `ProcessBuilder` with strict array arguments and sanitize all input parameters.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

            # Division by zero
            if re.search(r'/\s*0\b', clean_line):
                self.issues.append(
                    ReviewIssue(
                        category="Logic Bug",
                        severity="HIGH",
                        line=lineno,
                        title="Division by Zero in Java",
                        description="Literal division by zero detected in integer expression.",
                        impact="Throws `java.lang.ArithmeticException: / by zero` at runtime.",
                        recommendation="Ensure denominator is verified to be non-zero before dividing.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

            # Bare catch-all: catch (Exception e) or catch (Throwable t) with empty body
            if re.search(r'catch\s*\(\s*(Exception|Throwable)\s+\w+\s*\)', clean_line):
                self.issues.append(
                    ReviewIssue(
                        category="Code Quality",
                        severity="MEDIUM",
                        line=lineno,
                        title="Overly Broad `catch (Exception e)` Clause",
                        description="Catching generic `Exception` or `Throwable` catches unchecked runtime errors indiscriminately.",
                        impact="Masks critical bugs and makes failure diagnosis difficult.",
                        recommendation="Catch specific exception types (e.g. `IOException`, `SQLException`) or rethrow after logging.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

            # Unclosed Resource Streams (FileInputStream, FileReader, Socket)
            if re.search(r'new\s+(FileInputStream|FileReader|FileOutputStream|FileWriter|Socket|ServerSocket)\s*\(', clean_line):
                if "try (" not in self.code and "try(" not in self.code:
                    self.issues.append(
                        ReviewIssue(
                            category="Code Quality",
                            severity="MEDIUM",
                            line=lineno,
                            title="Potential Resource Leak (Unclosed Stream)",
                            description="I/O Stream or Socket instantiated without Java try-with-resources statement.",
                            impact="May leak operating system file handles and sockets, exhausting system file descriptors.",
                            recommendation="Wrap resource allocations in a `try (var stream = ...) {}` try-with-resources block.",
                            evidence=clean_line,
                            source="Deterministic (AST)"
                        )
                    )

            # SQL Injection pattern
            if re.search(r'\.executeQuery\s*\(\s*["\'].*\+.*\)', clean_line):
                self.issues.append(
                    ReviewIssue(
                        category="Security Vulnerability",
                        severity="CRITICAL",
                        line=lineno,
                        title="SQL Injection via String Concatenation",
                        description="Dynamic SQL query constructed using string concatenation instead of parameterized PreparedStatement.",
                        impact="Allows attackers to bypass authentication and manipulate database records.",
                        recommendation="Use `PreparedStatement` with parameterized placeholders (`?`) instead of string concatenation.",
                        evidence=clean_line,
                        source="Deterministic (AST)"
                    )
                )

        return self.issues

    def _check_delimiters(self):
        stack = []
        mapping = {')': '(', '}': '{', ']': '['}
        for lineno, line in enumerate(self.lines, start=1):
            for char in line:
                if char in "({[":
                    stack.append((char, lineno))
                elif char in ")}]":
                    if not stack or stack[-1][0] != mapping[char]:
                        self.issues.append(
                            ReviewIssue(
                                category="Syntax Error",
                                severity="CRITICAL",
                                line=lineno,
                                title="Mismatched / Unclosed Bracket in Java",
                                description=f"Unmatched closing delimiter `{char}` found.",
                                impact="Java code will fail compilation.",
                                recommendation=f"Ensure opening and closing delimiters match properly.",
                                evidence=line.strip(),
                                source="Deterministic (AST)"
                            )
                        )
                        return
                    stack.pop()
        if stack:
            unclosed, lineno = stack[0]
            self.issues.append(
                ReviewIssue(
                    category="Syntax Error",
                    severity="CRITICAL",
                    line=lineno,
                    title="Unclosed Delimiter in Java",
                    description=f"Opening delimiter `{unclosed}` at line {lineno} is never closed.",
                    impact="Java compiler will fail with syntax compilation error.",
                    recommendation="Add the matching closing delimiter.",
                    evidence=self.lines[lineno - 1].strip() if lineno <= len(self.lines) else "",
                    source="Deterministic (Static)"
                )
            )

    def _check_secrets(self):
        secret_patterns = [
            (r'(?i)(api[_-]?key|secret|token|password|auth_token)\s*=\s*["\']([A-Za-z0-9_\-]{8,})["\']', "Hardcoded API Key / Secret"),
            (r'AIzaSy[A-Za-z0-9_\-]{33}', "Google API Key Pattern"),
            (r'sk-[A-Za-z0-9]{32,}', "Secret Key Pattern"),
        ]
        for lineno, line in enumerate(self.lines, start=1):
            for pattern, title in secret_patterns:
                match = re.search(pattern, line)
                if match:
                    val = match.group(0)
                    if any(p in val.lower() for p in ["your_", "placeholder", "xxx", "example", "env"]):
                        continue
                    self.issues.append(
                        ReviewIssue(
                            category="Security Vulnerability",
                            severity="CRITICAL",
                            line=lineno,
                            title=title,
                            description="Hardcoded sensitive secret detected in Java source code.",
                            impact="Committing plaintext credentials allows unauthorized access to production APIs.",
                            recommendation="Load secrets from environment variables using `System.getenv()` or a secure vault.",
                            evidence=line.strip(),
                            source="Deterministic (AST)"
                        )
                    )


def run_static_analysis(code: str, language: str = "python") -> List[ReviewIssue]:
    """
    Public helper function to run deterministic static analysis on code
    supporting Python, C++, and Java.
    """
    if not code or not code.strip():
        return []
    
    lang = language.lower().strip()
    if lang in ("cpp", "c++", "c", "cxx"):
        analyzer = CppStaticAnalyzer(code)
        return analyzer.run()
    elif lang in ("java",):
        analyzer = JavaStaticAnalyzer(code)
        return analyzer.run()
    else:
        analyzer = PythonASTAnalyzer(code)
        return analyzer.run()

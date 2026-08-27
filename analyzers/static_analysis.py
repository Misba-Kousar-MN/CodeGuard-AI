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
                    # Exclude placeholders like 'your_api_key_here' or 'xxx'
                    val = match.group(0)
                    if any(p in val.lower() for p in ["your_", "placeholder", "xxx", "example", "env"]):
                        continue
                    self.issues.append(
                        ReviewIssue(
                            category="Security Vulnerability",
                            severity="CRITICAL",
                            line=lineno,
                            title=title,
                            description=f"Hardcoded sensitive secret detected in source code.",
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

    def visit_BinOp(self, node: ast.BinOp):
        # Detect division / modulo by zero or unvalidated denominator variable
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
            elif isinstance(node.right, ast.Name):
                self.issues.append(
                    ReviewIssue(
                        category="Logic Bug",
                        severity="MEDIUM",
                        line=node.lineno,
                        title=f"Potential Division by Zero (`{node.right.id}`)",
                        description=f"Division operation by denominator variable `{node.right.id}` without zero validation.",
                        impact=f"If `{node.right.id}` is 0, a `ZeroDivisionError` will be raised at runtime.",
                        recommendation=f"Validate denominator before dividing: `if {node.right.id} != 0:`.",
                        evidence=self._get_line_snippet(node.lineno),
                        source="Deterministic (AST)"
                    )
                )
        self.generic_visit(node)

    def _get_line_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""


def run_static_analysis(code: str) -> List[ReviewIssue]:
    """Public helper function to run Python AST static analysis."""
    if not code or not code.strip():
        return []
    analyzer = PythonASTAnalyzer(code)
    return analyzer.run()

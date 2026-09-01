import subprocess
import tempfile
import json
import os
from typing import List
from core.schemas import ReviewIssue

def run_ruff_analysis(code: str) -> List[ReviewIssue]:
    """
    Run Ruff static linter on Python code via subprocess and parse JSON output.
    Returns list of ReviewIssue items from Ruff linting.
    """
    if not code or not code.strip():
        return []

    issues: List[ReviewIssue] = []
    tmp_path = None

    try:
        # Write code to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        # Run ruff check with json output
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", tmp_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout:
            try:
                ruff_data = json.loads(result.stdout)
                for item in ruff_data:
                    code_rule = item.get("code", "")
                    message = item.get("message", "")
                    lineno = item.get("location", {}).get("row", 1)
                    
                    # Ignore pure cosmetic style / opinionated rules (import sorting I, formatting W292, pyupgrade UP, pylint PL, blind except BLE, try-pass S110/S112, etc.)
                    if code_rule.startswith(("I", "UP", "PL", "BLE", "TRY", "EM", "ERA", "D", "ANN", "RET", "SIM", "ARG", "PTH")) or code_rule in ("W292", "E501", "RUF012", "S110", "S112"):
                        continue

                    # Map Ruff severity
                    severity = "LOW"
                    category = "Code Quality"
                    if code_rule.startswith("S"): # Security (flake8-bandit)
                        category = "Security Vulnerability"
                        severity = "HIGH"
                    elif code_rule.startswith("F"): # Pyflakes (Logic / Undefined)
                        category = "Logic Bug"
                        severity = "HIGH"
                    elif code_rule.startswith("B"): # Bugbear
                        category = "Logic Bug"
                        severity = "MEDIUM"

                    issues.append(
                        ReviewIssue(
                            category=category,
                            severity=severity,
                            line=lineno,
                            title=f"Ruff [{code_rule}]: {message}",
                            description=f"Static linter rule {code_rule} triggered: {message}",
                            impact="Potential lint error or static code violation.",
                            recommendation=f"Resolve Ruff rule {code_rule}: {message}",
                            evidence=f"Line {lineno}: {message}",
                            source="Deterministic (AST)"
                        )
                    )
            except json.JSONDecodeError:
                pass
    except Exception as e:
        print(f"[RuffAnalyzer] Ruff analysis skipped/failed: {e}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return issues

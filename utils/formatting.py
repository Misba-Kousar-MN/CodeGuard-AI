import difflib

def generate_unified_diff(old_code: str, new_code: str, old_label: str = "Original Code", new_label: str = "Fixed Code") -> str:
    """Generates a unified text diff between old_code and new_code."""
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=old_label,
        tofile=new_label,
        n=3
    )
    return "".join(diff)


def get_severity_badge_html(severity: str) -> str:
    """Returns HTML styled pill badge for issue severity."""
    severity = severity.upper()
    styles = {
        "CRITICAL": "background: rgba(239, 68, 68, 0.15); color: #FCA5A5; border: 1px solid rgba(239, 68, 68, 0.3);",
        "HIGH": "background: rgba(249, 115, 22, 0.15); color: #FDBA74; border: 1px solid rgba(249, 115, 22, 0.3);",
        "MEDIUM": "background: rgba(245, 158, 11, 0.15); color: #FDE68A; border: 1px solid rgba(245, 158, 11, 0.3);",
        "LOW": "background: rgba(16, 185, 129, 0.15); color: #6EE7B7; border: 1px solid rgba(16, 185, 129, 0.3);"
    }
    style = styles.get(severity, "background: rgba(148, 163, 184, 0.15); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3);")
    return f'<span style="{style} padding: 3px 10px; border-radius: 9999px; font-weight: 600; font-size: 11px; letter-spacing: 0.04em;">{severity}</span>'


def get_category_badge_html(category: str) -> str:
    """Returns HTML styled pill badge for issue category."""
    styles = {
        "Security Vulnerability": "background: rgba(217, 119, 6, 0.15); color: #FDE68A; border: 1px solid rgba(217, 119, 6, 0.3);",
        "Logic Bug": "background: rgba(225, 29, 72, 0.15); color: #FECDD3; border: 1px solid rgba(225, 29, 72, 0.3);",
        "Code Quality": "background: rgba(37, 99, 235, 0.15); color: #93C5FD; border: 1px solid rgba(37, 99, 235, 0.3);",
        "Performance": "background: rgba(13, 148, 136, 0.15); color: #99F6E4; border: 1px solid rgba(13, 148, 136, 0.3);",
        "Syntax Error": "background: rgba(147, 51, 234, 0.15); color: #E9D5FF; border: 1px solid rgba(147, 51, 234, 0.3);"
    }
    style = styles.get(category, "background: rgba(148, 163, 184, 0.15); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3);")
    return f'<span style="{style} padding: 3px 10px; border-radius: 9999px; font-weight: 500; font-size: 11px;">{category}</span>'

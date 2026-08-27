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
    """Returns HTML styled badge for issue severity."""
    severity = severity.upper()
    colors = {
        "CRITICAL": "#ff4d4f",
        "HIGH": "#ff7a45",
        "MEDIUM": "#ffa940",
        "LOW": "#73d13d"
    }
    bg_color = colors.get(severity, "#8c8c8c")
    return f'<span style="background-color: {bg_color}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 12px;">{severity}</span>'


def get_category_badge_html(category: str) -> str:
    """Returns HTML styled badge for issue category."""
    colors = {
        "Security Vulnerability": "#d48806",
        "Logic Bug": "#cf1322",
        "Code Quality": "#096dd9",
        "Performance": "#389e0d",
        "Syntax Error": "#722ed1"
    }
    bg_color = colors.get(category, "#595959")
    return f'<span style="background-color: {bg_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{category}</span>'

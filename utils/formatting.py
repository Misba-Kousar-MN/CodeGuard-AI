import difflib
import re

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


def redact_secrets(text: str) -> str:
    """
    Redacts sensitive API key patterns (e.g. AIzaSy..., raw secrets) in display text.
    """
    if not text:
        return text
    # Replace AIza... API key strings
    text = re.sub(r'AIza[0-9A-Za-z_-]{15,}', '[REDACTED]', text)
    # Replace API_KEY = "..." string values
    text = re.sub(r'(API_KEY\s*=\s*["\'])[^\'"]+(["\'])', r'\1[REDACTED]\2', text, flags=re.IGNORECASE)
    return text


def get_severity_badge_html(severity: str) -> str:
    """Returns cute dreamy pastel pill badge for issue severity."""
    severity = severity.upper()
    styles = {
        "CRITICAL": "background: linear-gradient(135deg, #FFE4E6 0%, #FECDD3 100%); color: #BE123C; border: 1px solid #FDA4AF; box-shadow: 0 2px 6px rgba(244, 63, 94, 0.15);",
        "HIGH": "background: linear-gradient(135deg, #FFEDD5 0%, #FED7AA 100%); color: #C2410C; border: 1px solid #FDBA74; box-shadow: 0 2px 6px rgba(249, 115, 22, 0.15);",
        "MEDIUM": "background: linear-gradient(135deg, #FEF9C3 0%, #FEF08A 100%); color: #A16207; border: 1px solid #FDE047; box-shadow: 0 2px 6px rgba(234, 179, 8, 0.15);",
        "LOW": "background: linear-gradient(135deg, #DCFCE7 0%, #BBF7D0 100%); color: #15803D; border: 1px solid #86EFAC; box-shadow: 0 2px 6px rgba(34, 197, 94, 0.15);"
    }
    icons = {
        "CRITICAL": "🚨",
        "HIGH": "⚡",
        "MEDIUM": "🫧",
        "LOW": "🌿"
    }
    style = styles.get(severity, "background: #F3E8FF; color: #6B21A8; border: 1px solid #D8B4FE;")
    icon = icons.get(severity, "●")
    return f'<span style="{style} display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 11px; letter-spacing: 0.03em;">{icon} {severity}</span>'


def get_category_badge_html(category: str) -> str:
    """Returns cute dreamy pastel pill badge for issue category."""
    styles = {
        "Security Vulnerability": ("🛡️", "background: linear-gradient(135deg, #FEE2E2 0%, #FFEDD5 100%); color: #9A3412; border: 1px solid #FCA5A5;"),
        "Logic Bug": ("🐞", "background: linear-gradient(135deg, #FCE7F3 0%, #FBCFE8 100%); color: #9D174D; border: 1px solid #F472B6;"),
        "Code Quality": ("🪄", "background: linear-gradient(135deg, #E0E7FF 0%, #DDD6FE 100%); color: #4338CA; border: 1px solid #A5B4FC;"),
        "Performance": ("⚡", "background: linear-gradient(135deg, #CCFBF1 0%, #99F6E4 100%); color: #115E59; border: 1px solid #5EEAD4;"),
        "Syntax Error": ("🎀", "background: linear-gradient(135deg, #F3E8FF 0%, #E9D5FF 100%); color: #6B21A8; border: 1px solid #D8B4FE;")
    }
    icon, style = styles.get(category, ("●", "background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1;"))
    return f'<span style="{style} display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 11px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);">{icon} {category}</span>'

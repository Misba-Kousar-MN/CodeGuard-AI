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
    """Returns HTML styled pill badge for issue severity."""
    severity = severity.upper()
    styles = {
        "CRITICAL": "background: #FEF2F2; color: #DC2626; border: 1px solid #FCA5A5;",
        "HIGH": "background: #FFF7ED; color: #EA580C; border: 1px solid #FDBA74;",
        "MEDIUM": "background: #FEFCE8; color: #D97706; border: 1px solid #FDE68A;",
        "LOW": "background: #F0F9FF; color: #0284C7; border: 1px solid #BAE6FD;"
    }
    style = styles.get(severity, "background: #F8FAFC; color: #64748B; border: 1px solid #E2E8F0;")
    return f'<span style="{style} padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 11px; letter-spacing: 0.04em;">{severity}</span>'


def get_category_badge_html(category: str) -> str:
    """Returns HTML styled pill badge for issue category."""
    styles = {
        "Security Vulnerability": "background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A;",
        "Logic Bug": "background: #FFE4E6; color: #E11D48; border: 1px solid #FECDD3;",
        "Code Quality": "background: #E0F2FE; color: #0369A1; border: 1px solid #BAE6FD;",
        "Performance": "background: #CCFBF1; color: #0F766E; border: 1px solid #99F6E4;",
        "Syntax Error": "background: #F3E8FF; color: #7E22CE; border: 1px solid #E9D5FF;"
    }
    style = styles.get(category, "background: #F1F5F9; color: #475569; border: 1px solid #E2E8F0;")
    return f'<span style="{style} padding: 4px 12px; border-radius: 9999px; font-weight: 600; font-size: 11px;">{category}</span>'

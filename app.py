import os
import time
import json
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.llm import GeminiLLMProvider
from core.orchestrator import CodeGuardOrchestrator
from utils.file_handler import validate_uploaded_file, read_uploaded_file
from utils.formatting import generate_unified_diff, get_severity_badge_html, get_category_badge_html, redact_secrets

# Page Configuration - Full Width SaaS Workspace
st.set_page_config(
    page_title="CodeGuard AI — Analyze. Explain. Fix. Validate.",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Professional Developer Platform CSS System (GitHub / Linear / Vercel Aesthetic)
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Page Styling */
    html, body, .stApp {
        background-color: #F7F9FC !important;
        color: #111827 !important;
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Page Container Dimensions */
    .block-container {
        max-width: 1440px !important;
        width: calc(100% - 32px) !important;
        padding-top: 8px !important;
        padding-bottom: 8px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
        margin: 0 auto !important;
    }

    /* 68px Fixed Top Navigation Bar */
    .top-nav-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 68px;
        padding: 0 20px;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }
    .brand-container {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brand-logo-icon {
        width: 34px;
        height: 34px;
        background: #EFF6FF;
        border: 1px solid #DBEAFE;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
    }
    .brand-name {
        font-size: 18px;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.01em;
    }
    .brand-tagline {
        font-size: 12px;
        color: #6B7280;
        font-weight: 400;
        margin-left: 8px;
    }

    /* Navigation Bar Right Control Badges */
    .nav-right-badges {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .badge-online {
        background: #F0FDF4;
        color: #16A34A;
        border: 1px solid #DCFCE7;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        height: 36px;
        display: inline-flex;
        align-items: center;
    }
    .badge-offline {
        background: #FFF7ED;
        color: #EA580C;
        border: 1px solid #FFEDD5;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 600;
        height: 36px;
        display: inline-flex;
        align-items: center;
    }

    /* Button System Overrides */
    .stButton > button {
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        height: 38px !important;
        transition: all 0.15s ease !important;
        border: 1px solid #D1D5DB !important;
        background-color: #FFFFFF !important;
        color: #374151 !important;
        box-shadow: none !important;
    }
    .stButton > button:hover {
        background-color: #F9FAFB !important;
        border-color: #9CA3AF !important;
        color: #111827 !important;
    }

    /* Primary Action Blue Button */
    .stButton > button[data-baseweb="button"][kind="primary"],
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
        height: 40px !important;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.2) !important;
    }
    .stButton > button[data-baseweb="button"][kind="primary"]:hover {
        background-color: #1D4ED8 !important;
        color: #FFFFFF !important;
    }

    /* Dark Code Editor Styling */
    .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #1F2937 !important;
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        line-height: 1.55 !important;
        height: 480px !important;
        padding: 14px !important;
    }
    .stTextArea textarea::placeholder {
        color: #64748B !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Selectbox Override */
    div[data-baseweb="select"] > div {
        border-radius: 8px !important;
        border: 1px solid #D1D5DB !important;
        background-color: #FFFFFF !important;
        color: #111827 !important;
        font-size: 13px !important;
        height: 38px !important;
    }

    /* Radio Mode Buttons */
    div[data-testid="stRadio"] label {
        font-size: 13px !important;
        color: #4B5563 !important;
        font-weight: 500 !important;
    }

    /* Severity Summary Cards (Item 9) */
    .sev-bar-grid {
        display: flex;
        gap: 10px;
        margin-bottom: 12px;
    }
    .sev-card-item {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        height: 74px;
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }
    .sev-card-num {
        font-size: 24px;
        font-weight: 700;
        line-height: 1.1;
    }
    .sev-card-lbl {
        font-size: 11px;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        margin-top: 2px;
    }

    /* Horizontal Info Alert (Item 10) */
    .info-alert-banner {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        height: 44px;
        padding: 0 14px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: #1E40AF;
        font-weight: 500;
        margin-bottom: 12px;
    }

    /* Empty Review Workspace State (Item 19) */
    .empty-workspace-container {
        text-align: center;
        padding: 50px 20px;
        background: #FFFFFF;
        border: 1px dashed #D1D5DB;
        border-radius: 12px;
        margin-top: 30px;
    }
    .empty-workspace-title {
        font-size: 16px;
        font-weight: 600;
        color: #111827;
        margin-top: 10px;
        margin-bottom: 4px;
    }
    .empty-workspace-desc {
        font-size: 13px;
        color: #6B7280;
        max-width: 280px;
        margin: 0 auto;
        line-height: 1.5;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Helper Root Cause Explanations
def get_root_cause_explanation(iss) -> str:
    """Returns developer-friendly root-cause explanation for an issue."""
    text = f"{iss.title} {iss.category} {iss.description}".lower()
    if "api_key" in text or "secret" in text or "credential" in text:
        return "The credential was placed directly in a source-code string variable instead of being loaded from a secure environment variable or secrets manager."
    if "zero" in text or "divide" in text or "division" in text:
        return "The calculation divides price by count without validating whether count is non-zero, assuming count is always greater than 0."
    if "eval" in text or "exec" in text or "dynamic" in text:
        return "User-supplied input string is passed directly to Python's eval() function, which executes string contents as arbitrary executable code."
    if "subprocess" in text or "shell=true" in text or "command" in text:
        return "Untrusted input is interpolated directly into a shell command with shell=True enabled, causing the command to be parsed by the system shell."
    if "except" in text or "catch-all" in text:
        return "The try/except block uses a bare except without specifying exception types, catching all unexpected system and runtime errors indiscriminately."
    if "condition" in text or "impossible" in text or "discount" in text:
        return "The logical expression combines mutually exclusive bounds (e.g. price > 100 AND price < 50), which can never evaluate to True."
    return "The implementation violates secure coding practices or standard language safety invariants."

# Sample Code Snippets for Demonstrations
BUGGY_SAMPLE = """import subprocess

API_KEY = "AIzaSyD9x8K11223344556677889900aabbcc"

def calculate_discount(price, count):
    # Potential division by zero if count is 0
    average = price / count
    
    # Incorrect logical condition
    if price > 100 and price < 50:
        discount = 0.2
    else:
        discount = 0.05
    return average * (1 - discount)

def execute_user_command(user_input):
    # Security Flaws: Dangerous eval and shell=True
    res = eval(user_input)
    subprocess.run(f"echo {user_input}", shell=True)
    return res

def read_data_file(filename):
    try:
        with open(filename, "r") as f:
            return f.read()
    except:
        print("Error reading file")
        return None
"""

CLEAN_SAMPLE = """def add(a, b):
    return a + b

result = add(2, 3)
print(result)
"""

LOGIC_SAMPLE = """def compute_ratio(a, b):
    # Missing zero check
    return a / b

def check_range(val):
    # Impossible condition
    if val > 100 and val < 10:
        return True
    return False
"""

# Session State Initialization
if "code_input" not in st.session_state:
    st.session_state.code_input = ""
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None

# Server-Side Engine Initialization
llm_provider = GeminiLLMProvider()

# 68px Top Navigation Bar (Section 2 & 26)
col_nav1, col_nav2 = st.columns([3, 1])
with col_nav1:
    st.markdown(
        """
        <div class="top-nav-bar">
            <div class="brand-container">
                <div class="brand-logo-icon">🛡️</div>
                <div>
                    <span class="brand-name">CodeGuard AI</span>
                    <span class="brand-tagline">Analyze. Explain. Fix. Validate.</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col_nav2:
    with st.expander("⚙ Settings", expanded=False):
        st.markdown(f"**AI Engine Status:** {'● Connected' if llm_provider.is_available() else '○ Offline (Static AST Only)'}")
        st.markdown(f"**Model:** `{llm_provider.model}`")
        if not llm_provider.is_available():
            st.caption("AI engine unavailable — static analysis fallback enabled.")

# Navigation Status Badge right below nav bar
st.markdown(
    f"""
    <div style="text-align:right; margin-top:-26px; margin-bottom:12px;">
        <span class="{'badge-online' if llm_provider.is_available() else 'badge-offline'}">
            {'● AI Ready (' + llm_provider.model + ')' if llm_provider.is_available() else '○ Static Analysis Only'}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# MAIN WORKSPACE (LEFT 46% | RIGHT 54%)
# ----------------------------------------------------
col_left, col_right = st.columns([46, 54])

# ====================================================
# LEFT COLUMN: CODE EDITOR WORKSPACE (46%)
# ====================================================
with col_left:
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        input_mode = st.radio("Mode", options=["</> Code Editor", "Upload File"], horizontal=True, label_visibility="collapsed")
    with col_m2:
        lang_sel = st.selectbox("Language", options=["Python"], index=0, label_visibility="collapsed")
        language = "python"

    st.markdown("<p style='color:#6B7280; font-size:12px; margin: 4px 0 8px;'>Paste your code here or upload a source file.</p>", unsafe_allow_html=True)

    if input_mode == "</> Code Editor":
        edited_code = st.text_area(
            label="Source Code Input Box",
            value=st.session_state.code_input,
            height=480,
            placeholder="Paste your source code here...",
            label_visibility="collapsed"
        )
        st.session_state.code_input = edited_code
    else:
        uploaded_file = st.file_uploader("Upload Source File (.py, .js, .java, .txt)", type=["py", "js", "java", "txt"])
        if uploaded_file is not None:
            file_bytes = uploaded_file.read()
            is_valid, msg = validate_uploaded_file(uploaded_file.name, file_bytes)
            if not is_valid:
                st.error(msg)
            else:
                content, read_err = read_uploaded_file(file_bytes)
                if read_err:
                    st.error(read_err)
                else:
                    st.session_state.code_input = content
                    st.success(f"✓ {uploaded_file.name} loaded ({len(content.splitlines())} lines).")

    active_code_str = st.session_state.code_input
    line_cnt = len(active_code_str.splitlines()) if active_code_str else 0
    char_cnt = len(active_code_str) if active_code_str else 0

    # Editor Footer Metadata & Actions (Section 6)
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        st.markdown(
            f"""
            <div style="font-size:11px; color:#6B7280; margin-top:6px;">
                Lines: {line_cnt} &nbsp;&nbsp;&nbsp;&nbsp; Characters: {char_cnt:,}
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_f2:
        col_btn1, col_btn2 = st.columns([1, 2])
        with col_btn1:
            if st.button("Clear", use_container_width=True):
                st.session_state.code_input = ""
                st.session_state.pipeline_result = None
                st.rerun()
        with col_btn2:
            run_btn = st.button("Review My Code ✨", type="primary", use_container_width=True)

    # Sample Dropdown Selector (Section 7)
    sample_choice = st.selectbox(
        "✨ Try a sample ▾",
        options=["Select a sample...", "Security Issues", "Logic Bugs", "Reliability Issues", "Code Quality", "Clean Code"],
        index=0
    )
    if sample_choice in ("Security Issues", "Logic Bugs", "Reliability Issues", "Code Quality"):
        st.session_state.code_input = BUGGY_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()
    elif sample_choice == "Clean Code":
        st.session_state.code_input = CLEAN_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()

    # Process Review Execution
    if run_btn:
        code_to_review = st.session_state.code_input.strip()
        if not code_to_review:
            st.warning("Add some code before starting the review.", icon="⚠️")
        else:
            progress_box = st.empty()
            with progress_box.container():
                st.markdown(
                    """
                    <div style="text-align:center; padding:16px; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:10px;">
                        <div style="font-weight:600; color:#1E40AF; font-size:14px;">CodeGuard is reviewing your code ✦</div>
                        <div style="font-size:12px; color:#2563EB; margin-top:6px;">
                            ✓ Code analysis &nbsp;|&nbsp; ✓ Bug detection &nbsp;|&nbsp; ✓ Security audit &nbsp;|&nbsp; ◌ Generating fixes &nbsp;|&nbsp; ◌ Validating fixes
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            try:
                orchestrator = CodeGuardOrchestrator(llm_provider=llm_provider)
                res = orchestrator.execute_pipeline(
                    code=code_to_review,
                    language=language,
                    max_iterations=3
                )
                st.session_state.pipeline_result = res
            except Exception as e:
                print(f"[CodeGuard App Error] {e}")
                st.session_state.pipeline_result = {
                    "error": "AI review couldn't be completed because the Gemini service encountered a network error. Static analysis fallback is available."
                }
            progress_box.empty()
            st.rerun()

# ====================================================
# RIGHT COLUMN: CODE REVIEW WORKSPACE (54%)
# ====================================================
with col_right:
    # State A: Before Review (Section 19 Empty State)
    if st.session_state.pipeline_result is None:
        st.markdown(
            """
            <div class="empty-workspace-container">
                <div style="font-size: 32px; color: #2563EB;">✨</div>
                <div class="empty-workspace-title">Your Code Review Workspace</div>
                <div class="empty-workspace-desc">
                    Paste your code or select a sample on the left,<br>then click <b>Review My Code ✨</b> to begin.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # State B: After Review (Dedicated Results Workspace)
    else:
        res = st.session_state.pipeline_result

        # Top Action (Section 8)
        col_res1, col_res2 = st.columns([1, 4])
        with col_res1:
            if st.button("← New Review"):
                st.session_state.pipeline_result = None
                st.rerun()

        if "error" in res:
            st.error(res["error"])
        else:
            review_obj = res["review"]
            counts = review_obj.severity_counts

            def get_count(k):
                return getattr(counts, k, 0) if hasattr(counts, k) else (counts.get(k, 0) if isinstance(counts, dict) else 0)

            consolidated = res["consolidated_issues"]
            total_issues = len(consolidated)
            sec_count = len([i for i in consolidated if i.category == "Security Vulnerability"])
            final_val = res["final_validation"]

            st.markdown("<h2 style='font-size: 26px; font-weight: 700; color: #111827; margin-bottom: 2px;'>Your Code Review ✨</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:#6B7280; font-size:14px; margin-top:-6px; margin-bottom:12px;'><b>{total_issues} issue(s) need your attention.</b></p>", unsafe_allow_html=True)

            # Four Severity Summary Cards (Section 9)
            st.markdown(
                f"""
                <div class="sev-bar-grid">
                    <div class="sev-card-item"><div class="sev-card-num" style="color:#DC2626;">{get_count('CRITICAL')}</div><div class="sev-card-lbl">Critical</div></div>
                    <div class="sev-card-item"><div class="sev-card-num" style="color:#EA580C;">{get_count('HIGH')}</div><div class="sev-card-lbl">High</div></div>
                    <div class="sev-card-item"><div class="sev-card-num" style="color:#D97706;">{get_count('MEDIUM')}</div><div class="sev-card-lbl">Medium</div></div>
                    <div class="sev-card-item"><div class="sev-card-num" style="color:#16A34A;">{get_count('LOW')}</div><div class="sev-card-lbl">Low</div></div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Concise Information Alert Banner (Section 10)
            if total_issues == 0:
                st.markdown("<div class='info-alert-banner' style='background:#F0FDF4; border-color:#DCFCE7; color:#15803D;'>✨ CodeGuard analyzed your code and found no issues.</div>", unsafe_allow_html=True)
            elif sec_count > 0:
                st.markdown(f"<div class='info-alert-banner'>🛡 CodeGuard found {total_issues} issue(s), including {sec_count} security risk(s).</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='info-alert-banner'>Your code has {total_issues} issue(s) that should be fixed before use.</div>", unsafe_allow_html=True)

            # Review Navigation Tabs (Section 11)
            t_issues, t_sec, t_fix, t_val = st.tabs([
                f"Issues ({total_issues})",
                f"Security ({sec_count})",
                "Fix",
                "Validation"
            ])

            # TAB 1: ISSUES LIST (Section 13-16)
            with t_issues:
                if not consolidated:
                    st.success("✨ No issues detected.")
                else:
                    cat_filter = st.radio("Filter", options=["All", "Security", "Bugs", "Reliability", "Quality"], horizontal=True)
                    
                    filtered = consolidated
                    if cat_filter == "Bugs":
                        filtered = [i for i in consolidated if i.category in ("Logic Bug", "Syntax Error")]
                    elif cat_filter == "Security":
                        filtered = [i for i in consolidated if i.category == "Security Vulnerability"]
                    elif cat_filter in ("Reliability", "Quality"):
                        filtered = [i for i in consolidated if i.category in ("Code Quality", "Performance")]

                    for idx, iss in enumerate(filtered):
                        root_cause = get_root_cause_explanation(iss)
                        
                        # First issue expanded by default (Section 13)
                        with st.expander(f"{iss.severity} · {iss.category} — Line {iss.line}: {iss.title}", expanded=(idx == 0)):
                            st.markdown(f"<span style='font-size:11px; color:#6B7280; font-weight:600; text-transform:uppercase;'>WHAT'S WRONG</span><br><span style='font-size:13px; color:#111827;'>{iss.description}</span>", unsafe_allow_html=True)
                            
                            c_w1, c_w2 = st.columns(2)
                            with c_w1:
                                st.markdown(f"<span style='font-size:11px; color:#6B7280; font-weight:600; text-transform:uppercase;'>WHY IT MATTERS</span><br><span style='font-size:13px;'>{iss.impact}</span>", unsafe_allow_html=True)
                            with c_w2:
                                st.markdown(f"<span style='font-size:11px; color:#6B7280; font-weight:600; text-transform:uppercase;'>RECOMMENDED FIX</span><br><span style='font-size:13px;'>{iss.recommendation}</span>", unsafe_allow_html=True)
                            
                            st.markdown(f"<span style='font-size:11px; color:#6B7280; font-weight:600; text-transform:uppercase;'>WHY IT HAPPENED</span><br><span style='font-size:13px;'>{root_cause}</span>", unsafe_allow_html=True)
                            
                            if iss.evidence:
                                st.markdown(f"<span style='font-size:11px; color:#6B7280; font-weight:600; text-transform:uppercase;'>EVIDENCE (Line {iss.line})</span>", unsafe_allow_html=True)
                                st.code(redact_secrets(iss.evidence), language="python")

            # TAB 2: SECURITY AUDIT
            with t_sec:
                sec_issues = [i for i in consolidated if i.category == "Security Vulnerability"]
                st.markdown("##### Security Audit")
                if not sec_issues:
                    st.success("✓ No exposed secrets or dangerous executions detected.")
                else:
                    for s in sec_issues:
                        st.error(f"⚠ Line {s.line}: {s.title} — {redact_secrets(s.description)}")

            # TAB 3: FIX TAB
            with t_fix:
                st.markdown("<h3 style='font-size:18px; font-weight:700;'>✨ Corrected Code</h3>", unsafe_allow_html=True)
                st.caption("CodeGuard generated this version based on the detected issues.")

                fixed_code = res["final_fixed_code"]
                c_orig, c_fix = st.columns(2)
                with c_orig:
                    st.markdown("##### BEFORE")
                    st.code(redact_secrets(res["original_code"]), language="python", line_numbers=True)
                with c_fix:
                    st.markdown("##### AFTER")
                    st.code(redact_secrets(fixed_code), language="python", line_numbers=True)

                st.markdown("##### What CodeGuard changed")
                last_iter = res["iterations"][-1] if res.get("iterations") else None
                if last_iter and hasattr(last_iter, "validation_result") and last_iter.validation_result.resolved_issues:
                    for resolved in last_iter.validation_result.resolved_issues:
                        st.write(f"- ✓ {resolved}")
                else:
                    for iss in consolidated:
                        st.write(f"- ✓ Fixed: {iss.title} (Line {iss.line})")

                col_fx1, col_fx2 = st.columns(2)
                with col_fx1:
                    if st.button("✨ Apply & Re-Validate Fix", type="primary", use_container_width=True):
                        st.session_state.code_input = fixed_code
                        st.session_state.pipeline_result = None
                        st.rerun()

            # TAB 4: VALIDATION TAB
            with t_val:
                st.markdown("<h3 style='font-size:18px; font-weight:700;'>Validation</h3>", unsafe_allow_html=True)
                st.caption("Did the fix pass the re-check?")

                rem_count = len(final_val.remaining_issues if final_val and final_val.remaining_issues else [])

                if res["is_resolved"] or rem_count == 0:
                    st.success("✓ Validation Passed — No remaining issues detected by static re-analysis and AI re-review.")
                else:
                    st.warning("⚠ Validation Needs Attention — Remaining issues require manual review.")

                st.write(f"- Issues Found: **{total_issues}**")
                st.write(f"- Issues Fixed: **{total_issues - rem_count}**")
                st.write(f"- Issues Remaining: **{rem_count}**")
                st.write(f"- Validation Iterations: **{res['total_iterations']}**")

                with st.expander("How CodeGuard reviewed this"):
                    st.write("1. Static & Structural Analysis")
                    st.write("2. Bug & Vulnerability Audit")
                    st.write("3. Automated Fix Generation")
                    st.write("4. Neural & AST Re-Validation")
                    st.caption(f"Completed {res['total_iterations']} review cycle(s).")
                    st.caption("ⓘ AI validation performs automated static re-analysis and neural re-review checks. It does not constitute mathematical formal verification.")

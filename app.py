import os
import time
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.llm import GeminiLLMProvider
from core.orchestrator import CodeGuardOrchestrator
from utils.file_handler import validate_uploaded_file, read_uploaded_file
from utils.formatting import generate_unified_diff, get_severity_badge_html, get_category_badge_html, redact_secrets

# Page Configuration
st.set_page_config(
    page_title="CodeGuard AI — Analyze. Explain. Fix. Validate.",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dreamy Sky-Blue Desktop Two-Column UX CSS
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, .stApp {
        background: linear-gradient(180deg, #E0F2FE 0%, #F0F9FF 35%, #F8FAFC 100%) !important;
        color: #0F172A !important;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Full Width Container for Desktop Two-Column Layout */
    .block-container {
        max-width: 1380px !important;
        padding-top: 0.8rem !important;
        padding-bottom: 1.5rem !important;
        margin: 0 auto !important;
    }

    /* Clean Horizontal Header Bar */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 20px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(12px);
        border: 1px solid #BAE6FD;
        border-radius: 14px;
        margin-bottom: 14px;
        box-shadow: 0 4px 15px -2px rgba(56, 189, 248, 0.08);
    }
    .brand-title {
        font-size: 1.3rem;
        font-weight: 800;
        color: #0284C7;
        letter-spacing: -0.02em;
    }
    .brand-tagline {
        font-size: 0.8rem;
        color: #64748B;
        margin-left: 10px;
        font-weight: 500;
    }
    .status-badge-active {
        background: #F0FDF4;
        color: #16A34A;
        border: 1px solid #86EFAC;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .status-badge-offline {
        background: #FFF7ED;
        color: #EA580C;
        border: 1px solid #FDBA74;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    /* Card Panels */
    .workspace-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 4px 16px -4px rgba(56, 189, 248, 0.06);
        height: 100%;
    }

    /* Editor Box Styling */
    .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.86rem !important;
        height: 380px !important;
        line-height: 1.45 !important;
    }

    pre, code {
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 8px !important;
    }

    /* Primary Sky-Blue Action Button */
    .stButton > button {
        border-radius: 9px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }

    /* Metadata Counter Row */
    .editor-meta-row {
        display: flex;
        justify-content: space-between;
        font-size: 0.76rem;
        color: #64748B;
        font-weight: 600;
        margin-top: 4px;
        margin-bottom: 8px;
    }

    /* Compact Severity Metric Cards */
    .severity-bar {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }
    .severity-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 8px 14px;
        min-width: 85px;
        flex: 1;
        text-align: center;
        box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.03);
    }
    .severity-num {
        font-size: 1.25rem;
        font-weight: 800;
    }
    .severity-lbl {
        font-size: 0.68rem;
        color: #64748B;
        font-weight: 700;
        text-transform: uppercase;
    }

    .summary-callout {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 0.88rem;
        color: #0369A1;
        font-weight: 600;
        margin-bottom: 12px;
    }

    /* Empty State Container */
    .empty-state-box {
        text-align: center;
        padding: 40px 20px;
        background: #F8FAFC;
        border: 2px dashed #E2E8F0;
        border-radius: 14px;
        color: #64748B;
    }
    .empty-state-icon {
        font-size: 2.2rem;
        margin-bottom: 8px;
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

# Clean Horizontal Header Bar
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(
        """
        <div class="app-header">
            <div>
                <span class="brand-title">🛡️ CodeGuard AI</span>
                <span class="brand-tagline">Analyze. Explain. Fix. Validate.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col_h2:
    with st.expander("⚙ Settings", expanded=False):
        st.markdown(f"**AI Engine Status:** {'● Connected' if llm_provider.is_available() else '○ Offline (Static AST Only)'}")
        st.markdown(f"**Model:** `{llm_provider.model}`")
        if not llm_provider.is_available():
            st.caption("AI engine unavailable — static analysis fallback enabled.")

# Engine Status Badge right under header
st.markdown(
    f"""
    <div style="text-align:right; margin-top:-24px; margin-bottom:12px;">
        <span class="{'status-badge-active' if llm_provider.is_available() else 'status-badge-offline'}">
            {'● AI Ready (' + llm_provider.model + ')' if llm_provider.is_available() else '○ Static Analysis Mode'}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# MAIN DESKTOP TWO-COLUMN WORKSPACE
# ----------------------------------------------------
col_left, col_right = st.columns([48, 52])

# ====================================================
# LEFT COLUMN: CODE WORKSPACE
# ====================================================
with col_left:
    st.markdown("### Code Editor")
    st.markdown("<p style='color:#64748B; font-size:0.85rem; margin-top:-8px;'>Paste your code here or upload a source file.</p>", unsafe_allow_html=True)

    input_mode = st.radio("Mode", options=["Code Editor", "Upload File"], horizontal=True, label_visibility="collapsed")

    if input_mode == "Code Editor":
        edited_code = st.text_area(
            label="Source Code Input Box",
            value=st.session_state.code_input,
            height=380,
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

    # Metadata row below editor
    st.markdown(
        f"""
        <div class="editor-meta-row">
            <span>Lines: {line_cnt}</span>
            <span>Characters: {char_cnt:,}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Action Controls under Editor
    col_a1, col_a2, col_a3 = st.columns([2, 1, 2])
    with col_a1:
        lang_sel = st.selectbox("Language", options=["Python"], index=0, label_visibility="collapsed")
        language = "python"
    with col_a2:
        if st.button("Clear", use_container_width=True):
            st.session_state.code_input = ""
            st.session_state.pipeline_result = None
            st.rerun()
    with col_a3:
        run_btn = st.button("Review My Code ✨", type="primary", use_container_width=True)

    # Sample Dropdown Selector
    sample_choice = st.selectbox(
        "Try a Sample ▾",
        options=["Select a sample...", "Security Issues", "Logic Bugs", "Clean Code"],
        index=0
    )
    if sample_choice == "Security Issues":
        st.session_state.code_input = BUGGY_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()
    elif sample_choice == "Logic Bugs":
        st.session_state.code_input = LOGIC_SAMPLE
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
                    <div class="workspace-card" style="text-align:center; padding:20px; background:#F0F9FF; border:1px solid #BAE6FD;">
                        <div style="font-weight:700; color:#0284C7; font-size:1.05rem;">CodeGuard is reviewing your code ✦</div>
                        <div style="font-size:0.85rem; color:#0369A1; margin-top:8px;">
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
# RIGHT COLUMN: REVIEW WORKSPACE
# ====================================================
with col_right:
    # State A: Before Review (Empty State)
    if st.session_state.pipeline_result is None:
        st.markdown(
            """
            <div class="empty-state-box">
                <div class="empty-state-icon">✨</div>
                <div style="font-weight:700; font-size:1.1rem; color:#0F172A; margin-bottom:4px;">Your Code Review Workspace</div>
                <div style="font-size:0.86rem; color:#64748B;">
                    Paste your code or select a sample on the left,<br>then click <b>Review My Code ✨</b> to begin.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # State B: After Review (Dedicated Results Workspace)
    else:
        res = st.session_state.pipeline_result

        # Top Return Action
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

            st.markdown("### Your Code Review ✨")
            st.markdown(f"<p style='color:#475569; font-size:0.92rem; margin-top:-8px;'><b>{total_issues} issue(s) need your attention.</b></p>", unsafe_allow_html=True)

            # Four Compact Severity Summary Cards
            st.markdown(
                f"""
                <div class="severity-bar">
                    <div class="severity-card"><div class="severity-num" style="color:#EF4444;">{get_count('CRITICAL')}</div><div class="severity-lbl">Critical</div></div>
                    <div class="severity-card"><div class="severity-num" style="color:#F97316;">{get_count('HIGH')}</div><div class="severity-lbl">High</div></div>
                    <div class="severity-card"><div class="severity-num" style="color:#F59E0B;">{get_count('MEDIUM')}</div><div class="severity-lbl">Medium</div></div>
                    <div class="severity-card"><div class="severity-num" style="color:#0284C7;">{get_count('LOW')}</div><div class="severity-lbl">Low</div></div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Concise Summary Banner
            if total_issues == 0:
                st.markdown("<div class='summary-callout' style='background:#F0FDF4; border-color:#86EFAC; color:#15803D;'>✨ CodeGuard analyzed your code and found no issues.</div>", unsafe_allow_html=True)
            elif sec_count > 0:
                st.markdown(f"<div class='summary-callout'>CodeGuard found {total_issues} issue(s), including {sec_count} security risk(s).</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='summary-callout'>Your code has {total_issues} issue(s) that should be fixed before use.</div>", unsafe_allow_html=True)

            # Workspace Tabs
            t_issues, t_sec, t_fix, t_val = st.tabs([
                f"Issues ({total_issues})",
                "Security",
                "✨ Fix",
                "Validation"
            ])

            # TAB 1: ISSUES LIST
            with t_issues:
                if not consolidated:
                    st.success("✨ No issues detected.")
                else:
                    cat_filter = st.radio("Filter", options=["All", "Bugs", "Security", "Quality"], horizontal=True)
                    
                    filtered = consolidated
                    if cat_filter == "Bugs":
                        filtered = [i for i in consolidated if i.category in ("Logic Bug", "Syntax Error")]
                    elif cat_filter == "Security":
                        filtered = [i for i in consolidated if i.category == "Security Vulnerability"]
                    elif cat_filter == "Quality":
                        filtered = [i for i in consolidated if i.category in ("Code Quality", "Performance")]

                    for iss in filtered:
                        sev_badge = get_severity_badge_html(iss.severity)
                        cat_badge = get_category_badge_html(iss.category)
                        root_cause = get_root_cause_explanation(iss)
                        
                        with st.expander(f"{iss.severity} · {iss.category} — Line {iss.line}: {iss.title}"):
                            st.markdown(f"**WHAT'S WRONG:** {iss.description}")
                            st.markdown(f"**WHY IT HAPPENED:** {root_cause}")
                            st.markdown(f"**WHY IT MATTERS / RISK:** {iss.impact}")
                            st.markdown(f"**RECOMMENDED FIX:** {iss.recommendation}")
                            if iss.evidence:
                                st.markdown("**EVIDENCE:**")
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
                st.markdown("### ✨ Corrected Code")
                st.caption("CodeGuard generated this version based on the detected issues.")

                fixed_code = res["final_fixed_code"]
                c_orig, c_fix = st.columns(2)
                with c_orig:
                    st.markdown("##### BEFORE")
                    st.code(redact_secrets(res["original_code"]), language="python", line_numbers=True)
                with c_fix:
                    st.markdown("##### AFTER")
                    st.code(redact_secrets(fixed_code), language="python", line_numbers=True)

                st.markdown("##### WHAT CHANGED")
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
                st.markdown("### Validation")
                st.caption("Did the fix pass the re-check?")

                rem_count = len(final_val.remaining_issues if final_val and final_val.remaining_issues else [])

                if res["is_resolved"] or rem_count == 0:
                    st.success("✓ Fix validated — CodeGuard re-checked the corrected code.")
                    st.write(f"- Issues before fix: **{total_issues}**")
                    st.write("- Issues after fix: **0**")
                else:
                    st.warning("⚠ Some issues remain after validation.")
                    st.write(f"- Issues before fix: **{total_issues}**")
                    st.write(f"- Issues after fix: **{rem_count}**")

                with st.expander("How CodeGuard reviewed this"):
                    st.write("1. Static & Structural Analysis")
                    st.write("2. Bug & Vulnerability Audit")
                    st.write("3. Automated Fix Generation")
                    st.write("4. Neural & AST Re-Validation")
                    st.caption(f"Completed {res['total_iterations']} review cycle(s).")

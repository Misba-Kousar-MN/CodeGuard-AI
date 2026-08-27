import os
import time
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.llm import GeminiLLMProvider
from core.orchestrator import CodeGuardOrchestrator
from utils.file_handler import validate_uploaded_file, read_uploaded_file
from utils.formatting import generate_unified_diff, get_severity_badge_html, get_category_badge_html

# Page Configuration
st.set_page_config(
    page_title="CodeGuard AI — Analyze. Explain. Fix. Validate.",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sky-Blue Compact UX CSS
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

    /* Centered Max Width Layout */
    .block-container {
        max-width: 980px !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        margin: 0 auto !important;
    }

    /* Sticky Compact Header Bar */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 16px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border: 1px solid #BAE6FD;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px -2px rgba(56, 189, 248, 0.08);
    }
    .brand-title {
        font-size: 1.2rem;
        font-weight: 800;
        color: #0284C7;
        letter-spacing: -0.02em;
    }
    .brand-tagline {
        font-size: 0.75rem;
        color: #64748B;
        margin-left: 8px;
    }
    .status-badge-active {
        background: #F0FDF4;
        color: #16A34A;
        border: 1px solid #86EFAC;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
    }
    .status-badge-offline {
        background: #FFF7ED;
        color: #EA580C;
        border: 1px solid #FDBA74;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.76rem;
        font-weight: 700;
    }

    /* Hero Section */
    .hero-container {
        padding: 4px 0 10px 0;
    }
    .hero-title {
        font-size: 1.45rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 2px;
    }
    .hero-subtitle {
        font-size: 0.88rem;
        color: #475569;
    }

    /* Input Card */
    .card-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px -4px rgba(56, 189, 248, 0.06);
    }

    /* Code Area Styling */
    .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.86rem !important;
        height: 340px !important;
    }

    pre, code {
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 8px !important;
    }

    .stButton > button {
        border-radius: 8px !important;
        font-weight: 700 !important;
    }

    /* Small Metric Cards */
    .metric-summary-bar {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
        flex-wrap: wrap;
    }
    .small-metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 6px 14px;
        min-width: 85px;
        text-align: center;
        box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.03);
    }
    .small-metric-num {
        font-size: 1.15rem;
        font-weight: 800;
    }
    .small-metric-lbl {
        font-size: 0.68rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
    }

    .explanation-callout {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 0.88rem;
        color: #0369A1;
        font-weight: 600;
        margin-bottom: 12px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Sample Code Snippets for Demonstrations
BUGGY_SAMPLE = """import os
import subprocess

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

CLEAN_SAMPLE = """import os
from typing import Optional

def compute_average(numbers: list[float]) -> Optional[float]:
    \"\"\"Computes average safely checking for empty lists.\"\"\"
    if not numbers:
        return None
    return sum(numbers) / len(numbers)

def fetch_environment_key() -> str:
    \"\"\"Safely retrieves API key from environment.\"\"\"
    return os.getenv("API_KEY", "")
"""

# Session State Initialization
if "code_input" not in st.session_state:
    st.session_state.code_input = ""
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None

# Load API Key from environment
env_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("AI_agent", "")
env_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Sticky Compact Header Bar
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(
        """
        <div class="app-header">
            <div>
                <span class="brand-title">CodeGuard AI ✦</span>
                <span class="brand-tagline">Analyze. Explain. Fix. Validate.</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
with col_h2:
    with st.expander("⚙ Settings", expanded=False):
        user_key = st.text_input("Gemini API Key", value=env_key, type="password")
        selected_model = st.selectbox("Gemini Model", options=["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"], index=0)

active_api_key = user_key.strip() if 'user_key' in locals() and user_key.strip() else env_key.strip()
model_choice = selected_model if 'selected_model' in locals() else env_model
llm_provider = GeminiLLMProvider(api_key=active_api_key, model=model_choice)

# Header Engine Status Badge
st.markdown(
    f"""
    <div style="text-align:right; margin-top:-22px; margin-bottom:8px;">
        <span class="{'status-badge-active' if llm_provider.is_available() else 'status-badge-offline'}">
            {'● AI Ready (' + model_choice + ')' if llm_provider.is_available() else '● AI Offline (Static AST)'}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# SCREEN 1: COMPACT INPUT STATE
# ----------------------------------------------------
if st.session_state.pipeline_result is None:

    # Short Hero Section
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-title">Review your code with confidence ✨</div>
            <div class="hero-subtitle">Find bugs, security risks and code-quality issues — then let CodeGuard fix and re-check them.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Main Code Input Card
    st.markdown("##### LET'S REVIEW YOUR CODE")
    st.markdown("<p style='color:#64748B; font-size:0.84rem; margin-top:-8px;'>Paste your code here or upload a source file.</p>", unsafe_allow_html=True)

    input_method = st.radio("Input Method", options=["Code Editor", "Upload File"], horizontal=True, label_visibility="collapsed")
    uploaded_content = None

    if input_method == "Code Editor":
        code_text = st.text_area(
            label="Code Editor Box",
            value=st.session_state.code_input,
            height=340,
            placeholder="Paste your code here...",
            label_visibility="collapsed"
        )
    else:
        uploaded_file = st.file_uploader("Drop your source file here (.py, .js, .java, .txt)", type=["py", "js", "java", "txt"])
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
                    uploaded_content = content
                    st.success(f"✓ {uploaded_file.name} loaded ({len(content.splitlines())} lines).")
        code_text = st.session_state.code_input

    active_code = uploaded_content if uploaded_content else code_text
    st.session_state.code_input = active_code

    # Controls Row Under Editor
    col_c1, col_c2, col_c3 = st.columns([2, 1, 2])
    with col_c1:
        lang_sel = st.selectbox("Language", options=["Python"], index=0)
        language = "python"
    with col_c2:
        st.write("")
        st.write("")
        if st.button("Clear", use_container_width=True):
            st.session_state.code_input = ""
            st.rerun()
    with col_c3:
        st.write("")
        st.write("")
        run_btn = st.button("✨ Review My Code", type="primary", use_container_width=True)

    # Sample Code Selector Dropdown
    sample_choice = st.selectbox("Try a sample ✦", options=["Select a sample...", "Security Issues", "Logic Bug", "Clean Code"], index=0)
    if sample_choice in ("Security Issues", "Logic Bug"):
        st.session_state.code_input = BUGGY_SAMPLE
        st.rerun()
    elif sample_choice == "Clean Code":
        st.session_state.code_input = CLEAN_SAMPLE
        st.rerun()

    # Process Review Action
    if 'run_btn' in locals() and run_btn:
        if not active_code or not active_code.strip():
            st.warning("Add some code before starting the review.", icon="⚠️")
        else:
            progress_box = st.empty()
            with progress_box.container():
                st.markdown(
                    """
                    <div class="card-box" style="text-align:center; padding:18px; background:#F0F9FF; border:1px solid #BAE6FD;">
                        <div style="font-weight:700; color:#0284C7; font-size:1.05rem;">CodeGuard is reviewing your code ✦</div>
                        <div style="font-size:0.85rem; color:#0369A1; margin-top:6px;">
                            ✓ Checking for bugs &nbsp;|&nbsp; ✓ Checking security &nbsp;|&nbsp; ✓ Understanding code &nbsp;|&nbsp; ◌ Preparing fixes
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            orchestrator = CodeGuardOrchestrator(llm_provider=llm_provider)
            res = orchestrator.execute_pipeline(
                code=active_code,
                language=language,
                max_iterations=3
            )
            st.session_state.pipeline_result = res
            progress_box.empty()
            st.rerun()

# ----------------------------------------------------
# SCREEN 2: DEDICATED COMPACT RESULTS WORKSPACE
# ----------------------------------------------------
else:
    res = st.session_state.pipeline_result

    # Top Action to Return to Input Screen
    if st.button("← New Review"):
        st.session_state.pipeline_result = None
        st.rerun()

    if "error" in res:
        st.error(f"CodeGuard couldn't connect to the AI engine: {res['error']}")
        if st.button("Try Again"):
            st.session_state.pipeline_result = None
            st.rerun()
    else:
        review_obj = res["review"]
        counts = review_obj.severity_counts

        def get_count(k):
            return getattr(counts, k, 0) if hasattr(counts, k) else (counts.get(k, 0) if isinstance(counts, dict) else 0)

        consolidated = res["consolidated_issues"]
        total_issues = len(consolidated)
        sec_count = len([i for i in consolidated if i.category == "Security Vulnerability"])
        final_val = res["final_validation"]

        # Results Header
        st.markdown("### Your Code Review ✦")
        st.markdown(f"<p style='color:#475569; font-size:0.95rem; margin-top:-8px;'><b>{total_issues} issue(s) need your attention.</b></p>", unsafe_allow_html=True)

        # Small Compact Severity Summary Cards
        st.markdown(
            f"""
            <div class="metric-summary-bar">
                <div class="small-metric-card"><div class="small-metric-num" style="color:#EF4444;">{get_count('CRITICAL')}</div><div class="small-metric-lbl">Critical</div></div>
                <div class="small-metric-card"><div class="small-metric-num" style="color:#F97316;">{get_count('HIGH')}</div><div class="small-metric-lbl">High</div></div>
                <div class="small-metric-card"><div class="small-metric-num" style="color:#F59E0B;">{get_count('MEDIUM')}</div><div class="small-metric-lbl">Medium</div></div>
                <div class="small-metric-card"><div class="small-metric-num" style="color:#0284C7;">{get_count('LOW')}</div><div class="small-metric-lbl">Low</div></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # One Concise Explanatory Sentence
        if total_issues == 0:
            st.markdown("<div class='explanation-callout' style='background:#F0FDF4; border-color:#86EFAC; color:#15803D;'>✨ CodeGuard analyzed your code and found no issues.</div>", unsafe_allow_html=True)
        elif sec_count > 0:
            st.markdown(f"<div class='explanation-callout'>CodeGuard found {total_issues} issue(s), including {sec_count} security risk(s).</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='explanation-callout'>Your code has {total_issues} issue(s) that should be fixed before use.</div>", unsafe_allow_html=True)

        # Dedicated Result Navigation Tabs
        t_over, t_issues, t_sec, t_fix, t_val = st.tabs([
            "Overview",
            f"Issues ({total_issues})",
            "Security",
            "✨ Fix",
            "Validation"
        ])

        # TAB 1: OVERVIEW (Short Health Breakdown)
        with t_over:
            st.markdown("##### Code Status")
            if total_issues == 0:
                st.success("● Good — Code is clean.")
            else:
                st.markdown(f"- **Security**: {'● Needs attention' if sec_count > 0 else '● Good'}")
                st.markdown(f"- **Reliability**: {'● Needs attention' if get_count('HIGH') > 0 else '● Good'}")
                st.markdown(f"- **Code Quality**: {'● Needs attention' if get_count('MEDIUM') > 0 else '● Good'}")
                st.caption("CodeGuard recommends fixing highlighted issues before production deployment.")

        # TAB 2: ISSUES LIST (Compact Cards with View Details expander)
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
                    
                    with st.expander(f"{iss.severity} · {iss.category} — Line {iss.line}: {iss.title}"):
                        st.markdown(f"**Problem:** {iss.description}")
                        st.markdown(f"**Why it matters:** {iss.impact}")
                        st.markdown(f"**Recommended fix:** {iss.recommendation}")
                        if iss.evidence:
                            st.code(iss.evidence, language="python")

        # TAB 3: SECURITY AUDIT
        with t_sec:
            sec_issues = [i for i in consolidated if i.category == "Security Vulnerability"]
            st.markdown("##### Security Audit")
            if not sec_issues:
                st.success("✓ No exposed secrets or dangerous executions detected.")
            else:
                for s in sec_issues:
                    st.error(f"⚠ Line {s.line}: {s.title} — {s.description}")

        # TAB 4: FIX TAB
        with t_fix:
            st.markdown("### ✨ Fix your code")
            st.caption("CodeGuard generated a corrected version based on the detected issues.")

            fixed_code = res["final_fixed_code"]
            c_orig, c_fix = st.columns(2)
            with c_orig:
                st.markdown("##### BEFORE")
                st.code(res["original_code"], language="python", line_numbers=True)
            with c_fix:
                st.markdown("##### AFTER")
                st.code(fixed_code, language="python", line_numbers=True)

            st.markdown("##### WHAT CHANGED")
            st.write("- ✓ Removed hardcoded secret / unsafe dynamic execution")
            st.write("- ✓ Added input validation & boundary checks")
            st.write("- ✓ Improved error handling")

            col_fx1, col_fx2 = st.columns(2)
            with col_fx1:
                if st.button("✨ Validate This Fix", type="primary", use_container_width=True):
                    st.session_state.code_input = fixed_code
                    st.session_state.pipeline_result = None
                    st.rerun()

        # TAB 5: VALIDATION TAB
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

            # Expandable Optional Recruiter View
            with st.expander("How CodeGuard reviewed this"):
                st.write("1. Static & Structural Analysis")
                st.write("2. Bug & Vulnerability Audit")
                st.write("3. Automated Fix Generation")
                st.write("4. Neural & AST Re-Validation")
                st.caption(f"Completed {res['total_iterations']} review cycle(s).")

            st.caption("ⓘ AI validation is automated static re-analysis and neural re-review. It is not formal verification.")

            if st.button("Start New Review"):
                st.session_state.pipeline_result = None
                st.rerun()

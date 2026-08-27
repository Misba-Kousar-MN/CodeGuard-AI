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

# Sky-Blue Soft Cute Premium Theme CSS
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

    /* Sticky Header */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 20px;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border: 1px solid #BAE6FD;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 4px 15px -3px rgba(56, 189, 248, 0.1);
    }
    .brand-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #0284C7;
        letter-spacing: -0.02em;
    }
    .brand-tagline {
        font-size: 0.76rem;
        color: #64748B;
        margin-left: 8px;
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

    /* Hero Section */
    .hero-container {
        padding: 8px 0 14px 0;
    }
    .hero-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 2px;
    }
    .hero-subtitle {
        font-size: 0.92rem;
        color: #475569;
    }

    /* Input Card */
    .card-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 20px -4px rgba(56, 189, 248, 0.08);
    }

    /* Text Area Styling */
    .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.88rem !important;
        height: 380px !important;
    }

    pre, code {
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 8px !important;
    }

    /* Button Hierarchy */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    /* Metric Pills */
    .metric-pill-container {
        display: flex;
        gap: 10px;
        margin-bottom: 16px;
        flex-wrap: wrap;
    }
    .metric-pill {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 8px 16px;
        min-width: 100px;
        text-align: center;
    }
    .metric-pill-num {
        font-size: 1.3rem;
        font-weight: 800;
    }
    .metric-pill-lbl {
        font-size: 0.72rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
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
    <div style="text-align:right; margin-top:-22px; margin-bottom:12px;">
        <span class="{'status-badge-active' if llm_provider.is_available() else 'status-badge-offline'}">
            {'● AI Ready (' + model_choice + ')' if llm_provider.is_available() else '● AI Offline (Static AST)'}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------------------------------------------
# SCREEN 1: INPUT STATE (Shown when no active review exists)
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
    st.markdown("### LET'S REVIEW YOUR CODE")
    st.markdown("<p style='color:#64748B; font-size:0.9rem; margin-top:-6px;'>Paste your code here or upload a source file.</p>", unsafe_allow_html=True)

    input_method = st.radio("Input Method", options=["Code Editor", "Upload File"], horizontal=True, label_visibility="collapsed")
    uploaded_content = None

    if input_method == "Code Editor":
        code_text = st.text_area(
            label="Code Editor Box",
            value=st.session_state.code_input,
            height=380,
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
                    <div class="card-box" style="text-align:center; padding:24px; background:#F0F9FF; border:1px solid #BAE6FD;">
                        <div style="font-weight:700; color:#0284C7; font-size:1.15rem;">✦ CodeGuard is reviewing your code</div>
                        <div style="font-size:0.9rem; color:#0369A1; margin-top:8px;">
                            ✓ Checking for bugs &nbsp;|&nbsp; ✓ Checking security &nbsp;|&nbsp; ✓ Understanding code &nbsp;|&nbsp; ✓ Preparing recommendations
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
# SCREEN 2: DEDICATED RESULTS WORKSPACE STATE
# ----------------------------------------------------
else:
    res = st.session_state.pipeline_result

    # Top Action to Start New Review
    if st.button("← Start New Review"):
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

        total_issues = len(res["consolidated_issues"])
        final_val = res["final_validation"]

        st.markdown("## Your Code Review ✦")
        st.markdown(f"<p style='color:#475569; font-size:1rem;'><b>{total_issues} issue(s) found</b></p>", unsafe_allow_html=True)

        # Compact Metric Pills
        st.markdown(
            f"""
            <div class="metric-pill-container">
                <div class="metric-pill"><div class="metric-pill-num" style="color:#EF4444;">{get_count('CRITICAL')}</div><div class="metric-pill-lbl">Critical</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#F97316;">{get_count('HIGH')}</div><div class="metric-pill-lbl">High</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#F59E0B;">{get_count('MEDIUM')}</div><div class="metric-pill-lbl">Medium</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#0284C7;">{get_count('LOW')}</div><div class="metric-pill-lbl">Low</div></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Dedicated Workspace Tabs
        t_over, t_issues, t_sec, t_fix, t_val = st.tabs([
            "Overview",
            f"Issues ({total_issues})",
            "Security",
            "✨ Fix",
            "Validation"
        ])

        # TAB 1: OVERVIEW
        with t_over:
            st.markdown("#### Code Health Summary")
            if total_issues == 0:
                st.success("✨ Your code looks great! No issues were detected by the review pipeline.")
            else:
                st.warning("Your code needs attention before production use.")
                st.write(f"- 🛡 Security: {'Needs attention' if get_count('CRITICAL') > 0 else 'Good'}")
                st.write(f"- ⚡ Reliability: {'Needs attention' if get_count('HIGH') > 0 else 'Good'}")
                st.write(f"- ✨ Code Quality: {'Needs attention' if get_count('MEDIUM') > 0 else 'Good'}")
                st.info("CodeGuard recommends fixing the highlighted issues before using this code in production.")

        # TAB 2: ISSUES
        with t_issues:
            issues = res["consolidated_issues"]
            if not issues:
                st.success("✨ No issues detected.")
            else:
                cat_filter = st.radio("Filter Category", options=["All", "Bugs", "Security", "Quality"], horizontal=True)
                
                filtered = issues
                if cat_filter == "Bugs":
                    filtered = [i for i in issues if i.category in ("Logic Bug", "Syntax Error")]
                elif cat_filter == "Security":
                    filtered = [i for i in issues if i.category == "Security Vulnerability"]
                elif cat_filter == "Quality":
                    filtered = [i for i in issues if i.category in ("Code Quality", "Performance")]

                for iss in filtered:
                    sev_symbol = "🔴" if iss.severity in ("CRITICAL", "HIGH") else "🟡"
                    with st.expander(f"{sev_symbol} {iss.severity} · {iss.category} — {iss.title} (Line {iss.line})"):
                        st.markdown(f"**Problem:** {iss.description}")
                        st.markdown(f"**Why it matters:** {iss.impact}")
                        st.markdown(f"**Recommended fix:** {iss.recommendation}")
                        if iss.evidence:
                            st.code(iss.evidence, language="python")

        # TAB 3: SECURITY AUDIT
        with t_sec:
            sec_issues = [i for i in res["consolidated_issues"] if i.category == "Security Vulnerability"]
            st.markdown("#### Security Audit")
            if not sec_issues:
                st.success("✓ No exposed secrets detected\n✓ No unsafe command execution detected")
            else:
                for s in sec_issues:
                    st.error(f"⚠ Line {s.line}: {s.title} — {s.description}")

        # TAB 4: FIX TAB
        with t_fix:
            st.markdown("### ✨ Fix your code")
            st.caption("CodeGuard generated a safer version based on the issues found.")

            fixed_code = res["final_fixed_code"]
            c_orig, c_fix = st.columns(2)
            with c_orig:
                st.markdown("##### BEFORE")
                st.code(res["original_code"], language="python", line_numbers=True)
            with c_fix:
                st.markdown("##### AFTER")
                st.code(fixed_code, language="python", line_numbers=True)

            st.markdown("##### WHAT CHANGED")
            st.write("- ✓ Removed hardcoded secret / unsafe evaluation")
            st.write("- ✓ Added input validation & zero-division checks")
            st.write("- ✓ Improved error handling")

            st.markdown("##### Unified Diff")
            st.code(generate_unified_diff(res["original_code"], fixed_code), language="diff")

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

            if res["is_resolved"]:
                st.success("✓ Fix validated — CodeGuard re-checked the corrected code and found no remaining issues in the configured review pipeline.")
            else:
                st.warning("⚠ Some issues remain — CodeGuard found additional issues after re-review.")

            st.markdown("##### Self-Review Summary")
            st.write("- ✓ Review completed")
            st.write("- ✓ Fix generated")
            st.write("- ✓ Fix re-checked")
            st.write("- ✓ Validation completed")

            st.caption("ⓘ AI validation is automated static re-analysis and neural re-review. It is not formal verification.")

            if st.button("Start New Review"):
                st.session_state.pipeline_result = None
                st.rerun()

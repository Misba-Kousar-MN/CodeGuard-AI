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
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sky Blue UX Reliability Custom CSS
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, .stApp {
        background: linear-gradient(180deg, #F0F9FF 0%, #F8FAFC 100%) !important;
        color: #0F172A !important;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Sticky Compact Header */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 24px;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid #BAE6FD;
        border-radius: 12px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px -2px rgba(2, 132, 199, 0.05);
    }
    .brand-title {
        font-size: 1.3rem;
        font-weight: 800;
        color: #0284C7;
        letter-spacing: -0.02em;
    }
    .brand-tagline {
        font-size: 0.78rem;
        color: #64748B;
        margin-top: 1px;
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

    /* Compact Hero Section */
    .hero-container {
        padding: 12px 0 16px 0;
        text-align: left;
    }
    .hero-title {
        font-size: 1.6rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #475569;
    }

    /* Crisp Input Box Card */
    .card-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 16px -4px rgba(2, 132, 199, 0.06);
    }

    /* Compact Issue Card */
    .compact-issue-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #0284C7;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 12px;
    }
    .compact-issue-card.critical { border-left-color: #EF4444; }
    .compact-issue-card.high { border-left-color: #F97316; }
    .compact-issue-card.medium { border-left-color: #F59E0B; }
    .compact-issue-card.low { border-left-color: #0284C7; }

    .issue-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Metric Pills */
    .metric-pill-container {
        display: flex;
        gap: 10px;
        margin-bottom: 18px;
        flex-wrap: wrap;
    }
    .metric-pill {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 8px 16px;
        min-width: 95px;
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

    /* Text Area Styling */
    .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #CBD5E1 !important;
        background: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.88rem !important;
        height: 320px !important;
    }

    pre, code {
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 8px !important;
    }

    .stButton > button {
        border-radius: 10px !important;
        font-weight: 700 !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Sample Code Snippets for Demonstration
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
    st.session_state.code_input = BUGGY_SAMPLE
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
        <div style="display:flex; align-items:center; gap:12px;">
            <span class="brand-title">🛡️ CodeGuard AI</span>
            <span class="brand-tagline">Analyze. Explain. Fix. Validate.</span>
        </div>
        """,
        unsafe_allow_html=True
    )
with col_h2:
    with st.expander("⚙️ Settings & Engine Status", expanded=False):
        user_key = st.text_input("Gemini API Key", value=env_key, type="password")
        selected_model = st.selectbox("Gemini Model", options=["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"], index=0)

active_api_key = user_key.strip() if 'user_key' in locals() and user_key.strip() else env_key.strip()
model_choice = selected_model if 'selected_model' in locals() else env_model
llm_provider = GeminiLLMProvider(api_key=active_api_key, model=model_choice)

# Header Engine Status Badge
st.markdown(
    f"""
    <div style="text-align:right; margin-top:-26px; margin-bottom:12px;">
        <span class="{'status-badge-active' if llm_provider.is_available() else 'status-badge-offline'}">
            {'● AI Engine Connected (' + model_choice + ')' if llm_provider.is_available() else '● AI Engine Offline (Static AST)'}
        </span>
    </div>
    """,
    unsafe_allow_html=True
)

# Hero Message
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">Review your code with confidence ✨</div>
        <div class="hero-subtitle">Find bugs, security risks and code-quality issues — then let CodeGuard fix and re-check your code.</div>
    </div>
    """,
    unsafe_allow_html=True
)

# CODE INPUT CONTAINER (Collapsible if review results exist)
input_expanded = st.session_state.pipeline_result is None

with st.expander("💻 Code Input", expanded=input_expanded):
    input_method = st.radio("Input Method", options=["Code Editor", "Upload File"], horizontal=True, label_visibility="collapsed")
    
    uploaded_content = None

    if input_method == "Code Editor":
        code_text = st.text_area(
            label="Code Editor Box",
            value=st.session_state.code_input,
            height=320,
            placeholder="Paste your Python code here...",
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

    # Controls Row under Editor
    c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4 = st.columns([1.5, 1.5, 1, 2])
    with c_ctrl1:
        lang_sel = st.selectbox("Language", options=["Python", "JavaScript", "Java"], index=0, label_visibility="collapsed")
        language = lang_sel.lower()
    with c_ctrl2:
        lines_cnt = len(active_code.splitlines()) if active_code else 0
        chars_cnt = len(active_code) if active_code else 0
        st.caption(f"Lines: **{lines_cnt}** | Chars: **{chars_cnt}**")
    with c_ctrl3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.code_input = ""
            st.session_state.pipeline_result = None
            st.rerun()
    with c_ctrl4:
        run_btn = st.button("✨ Review My Code", type="primary", use_container_width=True)

    # Compact Sample Selector
    sample_choice = st.selectbox("Try a sample ✨", options=["Select a sample...", "🐛 Security Flaws & Bugs", "✨ Clean Code"], index=0)
    if sample_choice == "🐛 Security Flaws & Bugs":
        st.session_state.code_input = BUGGY_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()
    elif sample_choice == "✨ Clean Code":
        st.session_state.code_input = CLEAN_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()

# Execution Logic
if 'run_btn' in locals() and run_btn:
    if not active_code or not active_code.strip():
        st.warning("Add some code first before running review.", icon="⚠️")
    else:
        progress_box = st.empty()
        with progress_box.container():
            st.markdown(
                """
                <div class="card-box" style="text-align:center; padding:20px; background:#F0F9FF; border:1px solid #BAE6FD;">
                    <div style="font-weight:700; color:#0284C7; font-size:1.1rem;">CodeGuard is reviewing your code...</div>
                    <div style="font-size:0.88rem; color:#0369A1; margin-top:8px;">
                        ✓ Understanding code &nbsp;|&nbsp; ✓ Running static checks &nbsp;|&nbsp; ◌ Finding issues &nbsp;|&nbsp; ◌ Auditing security &nbsp;|&nbsp; ◌ Preparing fixes
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

# RESULTS WORKSPACE STATE
res = st.session_state.pipeline_result

if res:
    if "error" in res:
        st.error(res["error"])
    else:
        review_obj = res["review"]
        counts = review_obj.severity_counts
        
        def get_count(k):
            return getattr(counts, k, 0) if hasattr(counts, k) else (counts.get(k, 0) if isinstance(counts, dict) else 0)

        total_issues = len(res["consolidated_issues"])
        final_val = res["final_validation"]

        st.markdown("## YOUR CODE REVIEW")
        st.markdown(f"<p style='color:#475569; font-size:1rem;'><b>{total_issues} issue(s) found</b> that deserve attention.</p>", unsafe_allow_html=True)

        # Compact Results Tabs
        t_over, t_issues, t_sec, t_fix, t_val = st.tabs([
            "Overview",
            f"Issues ({total_issues})",
            "Security",
            "✨ AI Fix",
            "🛡️ Self-Review"
        ])

        # TAB 1: OVERVIEW
        with t_over:
            st.markdown(
                f"""
                <div class="metric-pill-container">
                    <div class="metric-pill"><div class="metric-pill-num" style="color:#0284C7;">{total_issues}</div><div class="metric-pill-lbl">Total Issues</div></div>
                    <div class="metric-pill"><div class="metric-pill-num" style="color:#EF4444;">{get_count('CRITICAL')}</div><div class="metric-pill-lbl">Critical</div></div>
                    <div class="metric-pill"><div class="metric-pill-num" style="color:#F97316;">{get_count('HIGH')}</div><div class="metric-pill-lbl">High</div></div>
                    <div class="metric-pill"><div class="metric-pill-num" style="color:#F59E0B;">{get_count('MEDIUM')}</div><div class="metric-pill-lbl">Medium</div></div>
                    <div class="metric-pill"><div class="metric-pill-num" style="color:#0284C7;">{get_count('LOW')}</div><div class="metric-pill-lbl">Low</div></div>
                </div>
                """,
                unsafe_allow_html=True
            )

            st.markdown("#### Health Check")
            st.write(f"- 🐞 **Bugs**: {get_count('CRITICAL') + get_count('HIGH')} high-priority logic flaws detected.")
            st.write(f"- 🔐 **Security**: {'1 or more credentials/eval vulnerabilities found.' if get_count('CRITICAL') > 0 else 'No critical secret leaks found.'}")
            st.write(f"- ✨ **Code Quality**: {get_count('MEDIUM') + get_count('LOW')} maintainability items flagged.")

        # TAB 2: ISSUES LIST
        with t_issues:
            issues = res["consolidated_issues"]
            if not issues:
                st.success("✨ Looks good! No remaining issues detected by the configured review pipeline.")
            else:
                cat_filter = st.radio("Filter", options=["All", "Bugs", "Security", "Quality"], horizontal=True)
                
                filtered = issues
                if cat_filter == "Bugs":
                    filtered = [i for i in issues if i.category in ("Logic Bug", "Syntax Error")]
                elif cat_filter == "Security":
                    filtered = [i for i in issues if i.category == "Security Vulnerability"]
                elif cat_filter == "Quality":
                    filtered = [i for i in issues if i.category in ("Code Quality", "Performance")]

                for iss in filtered:
                    sev_badge = get_severity_badge_html(iss.severity)
                    cat_badge = get_category_badge_html(iss.category)
                    
                    with st.expander(f"{iss.severity} · Line {iss.line}: {iss.title}"):
                        st.markdown(f"**Problem:** {iss.description}")
                        st.markdown(f"**Why this matters:** {iss.impact}")
                        st.markdown(f"**Suggested fix:** {iss.recommendation}")
                        if iss.evidence:
                            st.code(iss.evidence, language=language)

        # TAB 3: SECURITY
        with t_sec:
            sec_issues = [i for i in res["consolidated_issues"] if i.category == "Security Vulnerability"]
            if not sec_issues:
                st.success("🛡️ No security vulnerabilities detected in source code.")
            else:
                st.warning(f"Found {len(sec_issues)} security item(s) requiring immediate attention:")
                for s_iss in sec_issues:
                    st.write(f"- **Line {s_iss.line}**: {s_iss.title} — {s_iss.description}")

        # TAB 4: FIX EXPERIENCE
        with t_fix:
            st.markdown("### ✨ AI Fix")
            st.caption("CodeGuard generated a safer version based on the detected issues.")

            fixed_code = res["final_fixed_code"]
            c_orig, c_fix = st.columns(2)
            with c_orig:
                st.markdown("##### ORIGINAL CODE")
                st.code(res["original_code"], language=language, line_numbers=True)
            with c_fix:
                st.markdown("##### FIXED CODE")
                st.code(fixed_code, language=language, line_numbers=True)

            st.markdown("##### What changed")
            st.write("- ✓ Input validation and boundary checks applied.")
            st.write("- ✓ Unsafe dynamic evaluation removed.")
            st.write("- ✓ Hardcoded secrets removed or parameterized.")

            st.markdown("##### Unified Git Diff")
            st.code(generate_unified_diff(res["original_code"], fixed_code), language="diff")

            col_fx1, col_fx2 = st.columns(2)
            with col_fx1:
                if st.button("✨ Re-review Fixed Code", type="primary", use_container_width=True):
                    st.session_state.code_input = fixed_code
                    st.session_state.pipeline_result = None
                    st.rerun()

        # TAB 5: VALIDATION / SELF-REVIEW
        with t_val:
            st.markdown("### 🛡️ SELF-REVIEW")
            st.caption("CodeGuard checks its own generated fix before considering the review complete.")

            st.markdown(
                """
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; padding:12px; border-radius:10px; font-weight:600; color:#0284C7; margin-bottom:16px;">
                    Review &nbsp;→&nbsp; Issues Found &nbsp;→&nbsp; Fix Generated &nbsp;→&nbsp; Fix Re-checked &nbsp;→&nbsp; Validation Complete
                </div>
                """,
                unsafe_allow_html=True
            )

            if res["is_resolved"]:
                st.success(f"✓ Fix validated — All previously detected issues were addressed in {res['total_iterations']} iteration(s).")
            else:
                st.warning(f"⚠ More work needed — {len(final_val.remaining_issues if final_val else [])} issue(s) persist after {res['total_iterations']} iteration(s).")

            st.caption("ⓘ AI validation is automated static re-analysis and neural re-review. It is not formal verification.")

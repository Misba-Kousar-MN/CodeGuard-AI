import os
import time
import streamlit as st
from dotenv import load_dotenv

# Load env variables
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

# Dreamy Sky Blue / Soft Cute Premium Theme CSS
CUSTOM_CSS = """
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Dreamy Sky Page Background */
    html, body, .stApp {
        background: linear-gradient(180deg, #E0F2FE 0%, #F0F9FF 40%, #F8FAFC 100%) !important;
        color: #0F172A !important;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
    }

    /* Streamlit Chrome Minimization */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Dreamy Top Header Bar */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px 28px;
        background: rgba(255, 255, 255, 0.85);
        backdrop-filter: blur(12px);
        border: 1px solid #BAE6FD;
        border-radius: 20px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(56, 189, 248, 0.15);
    }
    .brand-title {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0284C7 0%, #38BDF8 50%, #6366F1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    .brand-tagline {
        font-size: 0.82rem;
        color: #64748B;
        margin-top: 2px;
        font-weight: 500;
    }
    .status-badge-active {
        background: #F0FDF4;
        color: #16A34A;
        border: 1px solid #86EFAC;
        padding: 6px 16px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .status-badge-offline {
        background: #FFF7ED;
        color: #EA580C;
        border: 1px solid #FDBA74;
        padding: 6px 16px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 700;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* Dreamy Hero Banner */
    .hero-container {
        text-align: center;
        padding: 32px 24px;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(224, 242, 254, 0.6) 100%);
        border: 1px solid #BAE6FD;
        border-radius: 24px;
        margin-bottom: 28px;
        box-shadow: 0 12px 35px -12px rgba(14, 165, 233, 0.12);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.03em;
        margin-bottom: 10px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #475569;
        max-width: 680px;
        margin: 0 auto;
        line-height: 1.6;
        font-weight: 500;
    }

    /* Crisp White Dreamy Card Box */
    .card-box {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(56, 189, 248, 0.08);
    }

    /* Cute Issue Card */
    .issue-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #0284C7;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 4px 15px -3px rgba(0, 0, 0, 0.03);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .issue-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px -5px rgba(2, 132, 199, 0.1);
    }
    .issue-card.critical { border-left-color: #EF4444; }
    .issue-card.high { border-left-color: #F97316; }
    .issue-card.medium { border-left-color: #F59E0B; }
    .issue-card.low { border-left-color: #0284C7; }

    .issue-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .issue-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
    }
    .issue-meta {
        font-size: 0.8rem;
        color: #64748B;
        font-weight: 500;
    }

    .section-label {
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 12px;
        margin-bottom: 4px;
    }
    .label-why { color: #DC2626; }
    .label-rec { color: #0284C7; }

    /* Compact Metric Pills */
    .metric-pill-container {
        display: flex;
        gap: 14px;
        margin-bottom: 24px;
        flex-wrap: wrap;
    }
    .metric-pill {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 12px 20px;
        min-width: 115px;
        text-align: center;
        box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.03);
    }
    .metric-pill-num {
        font-size: 1.5rem;
        font-weight: 800;
    }
    .metric-pill-lbl {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
        margin-top: 2px;
    }

    /* Dreamy Primary CTA Button */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }

    /* Text Area Styling */
    .stTextArea textarea {
        border-radius: 14px !important;
        border: 1px solid #CBD5E1 !important;
        background: #F8FAFC !important;
        color: #0F172A !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.92rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2) !important;
    }

    /* Code Blocks */
    pre, code {
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 12px !important;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 8px 16px;
        font-weight: 600;
    }

    /* Footer */
    .app-footer {
        text-align: center;
        padding: 32px 16px 16px 16px;
        color: #64748B;
        font-size: 0.85rem;
        border-top: 1px solid #E2E8F0;
        margin-top: 40px;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Sample Code Snippets for Quick Demonstration
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

# Load API Key from environment or input
env_key = os.getenv("GEMINI_API_KEY", "") or os.getenv("AI_agent", "")
env_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# Collapsible Settings Bar for API Key & Model Configuration
with st.expander("⚙️ Settings", expanded=False):
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        user_key = st.text_input(
            "Gemini API Key",
            value=env_key,
            type="password",
            help="Configured via .env or entered here. Never logged or stored."
        )
    with col_cfg2:
        selected_model = st.selectbox(
            "Gemini Model",
            options=["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"],
            index=0
        )

active_api_key = user_key.strip() or env_key.strip()
llm_provider = GeminiLLMProvider(api_key=active_api_key, model=selected_model)

# Top Application Header Bar
st.markdown(
    f"""
    <div class="app-header">
        <div>
            <div class="brand-title">🛡️ CodeGuard AI</div>
            <div class="brand-tagline">Analyze. Explain. Fix. Validate.</div>
        </div>
        <div>
            <span class="{'status-badge-active' if llm_provider.is_available() else 'status-badge-offline'}">
                {'● AI Engine Connected (' + selected_model + ')' if llm_provider.is_available() else '● AI Engine Offline (Static AST)'}
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Dreamy Hero Landing Section
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">Review your code with confidence ☁️</div>
        <div class="hero-subtitle">
            Find bugs, uncover security risks, understand what went wrong, and let AI fix and validate your code.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Main Code Input Card
st.markdown("### Let's review your code ✨")
st.markdown("<p style='color:#64748B; margin-top:-8px; margin-bottom:16px;'>Paste your code or upload a source file to get started.</p>", unsafe_allow_html=True)

# Sample Code Selector Section
st.markdown("<p style='font-size:0.88rem; font-weight:700; color:#475569; margin-bottom:8px;'>Not sure what to try? ✨</p>", unsafe_allow_html=True)
col_sm1, col_sm2, col_sm3, col_sm_space = st.columns([1.8, 1.5, 1.2, 4])
with col_sm1:
    if st.button("🐛 Security & Logic Flaws", use_container_width=True):
        st.session_state.code_input = BUGGY_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()
with col_sm2:
    if st.button("✨ Clean Code", use_container_width=True):
        st.session_state.code_input = CLEAN_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()
with col_sm3:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.code_input = ""
        st.session_state.pipeline_result = None
        st.rerun()

st.write("")

# Code Input & File Upload Tabs
input_tab_code, input_tab_upload = st.tabs(["💻 Code Editor", "☁️ Drop Source File"])

uploaded_content = None

with input_tab_code:
    code_text = st.text_area(
        label="Code Input Box",
        value=st.session_state.code_input,
        height=270,
        placeholder="Paste your Python code here...",
        label_visibility="collapsed"
    )

with input_tab_upload:
    st.markdown("##### ☁️ Drop your source file here")
    uploaded_file = st.file_uploader("Upload file (.py, .js, .java, .txt)", type=["py", "js", "java", "txt"])
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
                st.success(f"File '{uploaded_file.name}' loaded successfully ({len(content.splitlines())} lines).")

active_code = uploaded_content if uploaded_content else code_text

# Controls Row
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1.5, 2.5])
with col_ctrl1:
    lang_selection = st.selectbox(
        "Language Scope",
        options=["Python (Primary)", "JavaScript (Experimental)", "Java (Experimental)"],
        index=0
    )
    language = "python" if "Python" in lang_selection else "javascript" if "JavaScript" in lang_selection else "java"

with col_ctrl2:
    max_iters = st.slider("Max Self-Review Iterations", min_value=1, max_value=3, value=3, help="Max self-review fix cycles.")

with col_ctrl3:
    st.write("")
    st.write("")
    run_btn = st.button("✨ Review My Code", type="primary", use_container_width=True)

# Process Pipeline Execution
if run_btn:
    if not active_code or not active_code.strip():
        st.warning("Please paste source code or upload a file before running review.", icon="⚠️")
    else:
        # Dreamy Loading Progress Stepper
        progress_placeholder = st.empty()
        with progress_placeholder.container():
            st.markdown(
                """
                <div class="card-box" style="text-align: center; padding: 32px; background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%); border: 1px solid #BAE6FD;">
                    <div style="font-size: 1.5rem; margin-bottom: 4px;">☁️</div>
                    <div style="font-size: 1.25rem; font-weight: 800; color: #0284C7; margin-bottom: 14px;">
                        CodeGuard is thinking...
                    </div>
                    <div style="font-size: 0.95rem; color: #0369A1; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-weight: 600;">
                        <span>✓ Understanding your code</span>
                        <span>✓ Running static analysis</span>
                        <span>✓ Reviewing bugs</span>
                        <span>✓ Checking security</span>
                        <span>✓ Preparing recommendations</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        orchestrator = CodeGuardOrchestrator(llm_provider=llm_provider)
        res = orchestrator.execute_pipeline(
            code=active_code,
            language=language,
            max_iterations=max_iters
        )
        st.session_state.pipeline_result = res
        progress_placeholder.empty()
        st.rerun()

# Render Pipeline Dashboard Results
res = st.session_state.pipeline_result

if res:
    st.divider()

    if "error" in res:
        st.markdown(
            f"""
            <div class="card-box" style="border-left: 5px solid #EF4444;">
                <div style="font-size: 1.1rem; font-weight: 700; color: #DC2626;">Something went wrong</div>
                <div style="color: #475569; margin-top: 4px;">{res['error']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        review_obj = res["review"]
        counts = review_obj.severity_counts
        
        def get_count(k):
            return getattr(counts, k, 0) if hasattr(counts, k) else (counts.get(k, 0) if isinstance(counts, dict) else 0)

        total_issues = len(res["consolidated_issues"])
        final_val = res["final_validation"]

        # Results Summary Header
        st.markdown("### Your Code Review ✨")
        st.markdown(
            f"<p style='color:#475569; font-size:1.05rem; margin-top:-6px;'>We found <b>{total_issues} thing(s) worth taking a closer look at</b>.</p>",
            unsafe_allow_html=True
        )

        # Compact Metric Pills
        st.markdown(
            f"""
            <div class="metric-pill-container">
                <div class="metric-pill"><div class="metric-pill-num" style="color:#DC2626;">{get_count('CRITICAL')}</div><div class="metric-pill-lbl">🔴 Critical</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#EA580C;">{get_count('HIGH')}</div><div class="metric-pill-lbl">🟠 High</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#D97706;">{get_count('MEDIUM')}</div><div class="metric-pill-lbl">🟡 Medium</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#0284C7;">{get_count('LOW')}</div><div class="metric-pill-lbl">🔵 Low</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#7E22CE;">{res['total_iterations']}</div><div class="metric-pill-lbl">🔄 Iterations</div></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Validation Verdict Status Callout
        if final_val:
            if res["is_resolved"]:
                st.markdown(
                    f"""
                    <div style="background: #F0FDF4; border: 1px solid #86EFAC; padding: 16px 24px; border-radius: 16px; margin-bottom: 24px; color: #15803D; font-weight: 700; font-size: 1rem;">
                        ✨ Looking good! — No remaining issues detected by the configured review pipeline ({res['total_iterations']} iteration(s)).
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style="background: #FEF2F2; border: 1px solid #FCA5A5; padding: 16px 24px; border-radius: 16px; margin-bottom: 24px; color: #B91C1C; font-weight: 700; font-size: 1rem;">
                        ⚠️ ISSUES REMAINING — {len(final_val.remaining_issues)} issue(s) persist after {res['total_iterations']} iteration(s).
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # Main Results Tabs
        tab_rev_overview, tab_rev_issues, tab_rev_fix, tab_rev_val = st.tabs([
            "📊 Overview & Structure",
            "🐞 Detected Issues & Audit",
            "✨ AI Fix & Code Comparison",
            "🛡️ Self-Review & Validation History"
        ])

        # TAB 1: OVERVIEW & ANALYSIS
        with tab_rev_overview:
            analysis = res["analysis"]
            st.markdown("##### Agent 1: Code Structure & Purpose")
            st.write(f"**Detected Language:** `{analysis.language}`")
            st.write(f"**Primary Purpose:** {analysis.purpose}")
            st.info(f"**Executive Summary:** {analysis.summary}")

            col_o1, col_o2 = st.columns(2)
            with col_o1:
                st.markdown("###### Code Components")
                if analysis.components:
                    for comp in analysis.components:
                        st.markdown(f"- `{comp}`")
                else:
                    st.caption("No explicit components identified.")
            with col_o2:
                st.markdown("###### High-Risk Control Flows")
                if analysis.risk_areas:
                    for risk in analysis.risk_areas:
                        st.markdown(f"- ⚠️ {risk}")
                else:
                    st.caption("No high-risk control flows detected.")

        # TAB 2: DETECTED ISSUES & AUDIT
        with tab_rev_issues:
            issues = res["consolidated_issues"]
            if not issues:
                st.markdown(
                    """
                    <div class="card-box" style="text-align:center; padding:36px;">
                        <div style="font-size:1.8rem; margin-bottom:6px;">✨ Looking good!</div>
                        <div style="color:#64748B;">No issues were detected by the configured review pipeline.</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                cat_filter = st.radio(
                    "Filter Findings",
                    options=["All", "🐞 Bugs", "🔐 Security", "✨ Quality"],
                    horizontal=True
                )
                
                filtered_issues = issues
                if cat_filter == "🐞 Bugs":
                    filtered_issues = [i for i in issues if i.category in ("Logic Bug", "Syntax Error")]
                elif cat_filter == "🔐 Security":
                    filtered_issues = [i for i in issues if i.category == "Security Vulnerability"]
                elif cat_filter == "✨ Quality":
                    filtered_issues = [i for i in issues if i.category in ("Code Quality", "Performance")]

                for iss in filtered_issues:
                    sev_html = get_severity_badge_html(iss.severity)
                    cat_html = get_category_badge_html(iss.category)
                    st.markdown(
                        f"""
                        <div class="issue-card {iss.severity.lower()}">
                            <div class="issue-header">
                                <div>{sev_html} &nbsp; {cat_html} &nbsp; <span class="issue-title">Line {iss.line}: {iss.title}</span></div>
                                <span class="issue-meta">Source: {iss.source}</span>
                            </div>
                            <p style="margin: 8px 0 6px 0; color: #334155;"><b>Problem:</b> {iss.description}</p>
                            <div class="section-label label-why">Why this matters</div>
                            <p style="margin-bottom: 6px; color: #DC2626; font-size: 0.92rem;">{iss.impact}</p>
                            <div class="section-label label-rec">Suggested Fix</div>
                            <p style="margin-bottom: 6px; color: #0284C7; font-size: 0.92rem;">{iss.recommendation}</p>
                            {f"<pre style='background:#F8FAFC; border:1px solid #E2E8F0; padding:10px; border-radius:10px; margin-top:8px; font-size:0.85rem;'>{iss.evidence}</pre>" if iss.evidence else ""}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # TAB 3: AI FIX & COMPARISON
        with tab_rev_fix:
            st.markdown("### ✨ AI Fix")
            st.markdown("<p style='color:#64748B;'>CodeGuard found the problem. Here's a safer version.</p>", unsafe_allow_html=True)

            fixed_code = res["final_fixed_code"]
            
            c_orig, c_fix = st.columns(2)
            with c_orig:
                st.markdown("##### 🔴 ORIGINAL CODE")
                st.code(res["original_code"], language=language, line_numbers=True)
            with c_fix:
                st.markdown("##### 🟢 FIXED CODE")
                st.code(fixed_code, language=language, line_numbers=True)

            st.markdown("##### 📜 Unified Git Diff")
            diff_text = generate_unified_diff(res["original_code"], fixed_code)
            if diff_text:
                st.code(diff_text, language="diff")
            else:
                st.info("No line changes detected between original and fixed code.")

        # TAB 4: SELF-REVIEW & VALIDATION HISTORY
        with tab_rev_val:
            st.markdown("### 🛡️ Self-Review")
            st.caption("Visualizing the agentic validation loop: Review → Issues Found → AI Fix → Re-review → Validation")

            iterations = res["iterations"]
            if not iterations:
                st.info("Original code passed review with 0 required fixing cycles.")
            else:
                for it in iterations:
                    val = it.validation_result
                    icon = "🟢" if val.validation_status == "PASSED AI RE-REVIEW" else "🟠"
                    with st.expander(f"{icon} Iteration {it.iteration_number} — Status: {val.validation_status}", expanded=(it.iteration_number == len(iterations))):
                        st.write(f"**Validation Summary:** {val.summary}")

                        c_val1, c_val2, c_val3 = st.columns(3)
                        with c_val1:
                            st.markdown(f"**Resolved ({len(val.resolved_issues)})**")
                            for r_title in val.resolved_issues:
                                st.markdown(f"- ✅ {r_title}")
                        with c_val2:
                            st.markdown(f"**Remaining ({len(val.remaining_issues)})**")
                            for rem in val.remaining_issues:
                                st.markdown(f"- ⚠️ Line {rem.line}: {rem.title}")
                        with c_val3:
                            st.markdown(f"**Newly Introduced ({len(val.new_issues)})**")
                            for new_i in val.new_issues:
                                st.markdown(f"- 🔴 Line {new_i.line}: {new_i.title}")

            st.divider()
            st.caption("ℹ️ **Validation Disclaimer**: AI validation is automated static re-analysis and neural re-review; it is not formal verification.")
else:
    # Dreamy Pre-Analysis Empty State
    st.markdown(
        """
        <div class="card-box" style="text-align: center; padding: 48px 24px; background: linear-gradient(180deg, #FFFFFF 0%, #F0F9FF 100%);">
            <div style="font-size: 2.2rem; margin-bottom: 8px;">☁️</div>
            <div style="font-size: 1.35rem; font-weight: 800; color: #0F172A; margin-bottom: 8px;">
                Your code review starts here
            </div>
            <div style="font-size: 0.98rem; color: #64748B; max-width: 520px; margin: 0 auto;">
                Paste some code above or try one of the example buttons to run static analysis and multi-agent AI review.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# Soft Minimal Product Footer
st.markdown(
    """
    <div class="app-footer">
        <b>🛡️ CodeGuard AI</b> &nbsp;•&nbsp; Analyze. Explain. Fix. Validate.<br>
        <span style="font-size:0.78rem; color:#94A3B8;">AI-powered code review with automated static analysis and self-review validation.</span>
    </div>
    """,
    unsafe_allow_html=True
)

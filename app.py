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
    page_icon="◇",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sophisticated Soft/Dark Premium Theme CSS
CUSTOM_CSS = """
<style>
    /* Dark Base Theme & Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, .stApp {
        background-color: #0B0F19;
        color: #E2E8F0;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }

    /* Hide Streamlit Chrome Noise */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Top Header Bar */
    .app-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        background: #111827;
        border-bottom: 1px solid #1F2937;
        border-radius: 12px;
        margin-bottom: 24px;
    }
    .brand-title {
        font-size: 1.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818CF8 0%, #C084FC 50%, #F472B6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    .brand-tagline {
        font-size: 0.8rem;
        color: #9CA3AF;
        margin-top: 2px;
        font-weight: 500;
    }
    .status-badge-active {
        background: rgba(16, 185, 129, 0.12);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .status-badge-offline {
        background: rgba(245, 158, 11, 0.12);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.3);
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* Hero Banner */
    .hero-container {
        text-align: center;
        padding: 20px 10px 24px 10px;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        color: #F8FAFC;
        letter-spacing: -0.03em;
        margin-bottom: 8px;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #94A3B8;
        max-width: 640px;
        margin: 0 auto;
        line-height: 1.5;
    }

    /* Compact Cards */
    .card-box {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }

    /* Issue Card */
    .issue-card {
        background: #131C2E;
        border: 1px solid #1E293B;
        border-left: 4px solid #6366F1;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 16px;
        transition: transform 0.15s ease;
    }
    .issue-card:hover {
        border-color: #334155;
    }
    .issue-card.critical { border-left-color: #EF4444; }
    .issue-card.high { border-left-color: #F97316; }
    .issue-card.medium { border-left-color: #F59E0B; }
    .issue-card.low { border-left-color: #10B981; }

    .issue-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }
    .issue-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #F1F5F9;
    }
    .issue-meta {
        font-size: 0.82rem;
        color: #64748B;
    }
    
    .section-label {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-top: 10px;
        margin-bottom: 2px;
    }
    .label-why { color: #FCA5A5; }
    .label-rec { color: #6EE7B7; }

    /* Summary Metric Pills */
    .metric-pill-container {
        display: flex;
        gap: 12px;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .metric-pill {
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 10px 18px;
        min-width: 110px;
        text-align: center;
    }
    .metric-pill-num {
        font-size: 1.4rem;
        font-weight: 700;
    }
    .metric-pill-lbl {
        font-size: 0.75rem;
        color: #94A3B8;
        font-weight: 500;
        text-transform: uppercase;
    }

    /* Primary Accent Button */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    /* Custom Code Fonts */
    pre, code, textarea {
        font-family: 'JetBrains Mono', monospace !important;
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
with st.expander("⚙️ Engine & API Configuration Settings", expanded=False):
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
            <div class="brand-title">◇ CodeGuard AI</div>
            <div class="brand-tagline">Analyze. Explain. Fix. Validate.</div>
        </div>
        <div>
            <span class="{'status-badge-active' if llm_provider.is_available() else 'status-badge-offline'}">
                {'🟢 AI Engine ● Ready (' + selected_model + ')' if llm_provider.is_available() else '🟠 AI Engine ● Offline (Static AST)'}
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Hero Landing Section
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-title">Review your code with confidence.</div>
        <div class="hero-subtitle">
            Detect logical bugs, security vulnerabilities, and quality flaws — then let CodeGuard generate, validate, and re-review safer code for you.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Quick Sample Buttons Bar
col_sm1, col_sm2, col_sm3, col_sm_space = st.columns([1.5, 1.3, 1.2, 4])
with col_sm1:
    if st.button("🐛 Buggy Sample Code", use_container_width=True):
        st.session_state.code_input = BUGGY_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()
with col_sm2:
    if st.button("✨ Clean Sample Code", use_container_width=True):
        st.session_state.code_input = CLEAN_SAMPLE
        st.session_state.pipeline_result = None
        st.rerun()
with col_sm3:
    if st.button("🗑️ Clear Code", use_container_width=True):
        st.session_state.code_input = ""
        st.session_state.pipeline_result = None
        st.rerun()

# Main Code Input Card
st.markdown("#### 💻 CODE INPUT")

input_tab_code, input_tab_upload = st.tabs(["💻 Code Editor", "📁 Drop Source File"])

uploaded_content = None

with input_tab_code:
    code_text = st.text_area(
        label="Code Input Box",
        value=st.session_state.code_input,
        height=260,
        placeholder="Paste your source code here or select a sample above...",
        label_visibility="collapsed"
    )

with input_tab_upload:
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
                st.success(f"File '{uploaded_file.name}' loaded ({len(content.splitlines())} lines).")

active_code = uploaded_content if uploaded_content else code_text

# Controls Bar
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1.5, 2.5])
with col_ctrl1:
    lang_selection = st.selectbox(
        "Language Scope",
        options=["Python (Primary)", "JavaScript (Experimental)", "Java (Experimental)"],
        index=0
    )
    language = "python" if "Python" in lang_selection else "javascript" if "JavaScript" in lang_selection else "java"

with col_ctrl2:
    max_iters = st.slider("Max Iterations", min_value=1, max_value=3, value=3, help="Max self-review fix cycles.")

with col_ctrl3:
    st.write("")
    st.write("")
    run_btn = st.button("✨ Review My Code", type="primary", use_container_width=True)

# Process Pipeline Execution
if run_btn:
    if not active_code or not active_code.strip():
        st.warning("Please paste source code or upload a file before running review.", icon="⚠️")
    else:
        # Polished Loading Stepper Experience
        progress_placeholder = st.empty()
        with progress_placeholder.container():
            st.markdown(
                """
                <div class="card-box" style="text-align: center; padding: 30px;">
                    <div style="font-size: 1.2rem; font-weight: 700; color: #818CF8; margin-bottom: 12px;">
                        ✦ CodeGuard AI Multi-Agent Pipeline Running...
                    </div>
                    <div style="font-size: 0.95rem; color: #94A3B8; display: flex; justify-content: center; gap: 24px;">
                        <span>✓ Understanding Code</span>
                        <span>✓ Static AST Audit</span>
                        <span>✓ Multi-Agent Review</span>
                        <span>✓ Fix & Self-Validation</span>
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
        st.error(res["error"])
    else:
        review_obj = res["review"]
        counts = review_obj.severity_counts
        
        def get_count(k):
            return getattr(counts, k, 0) if hasattr(counts, k) else (counts.get(k, 0) if isinstance(counts, dict) else 0)

        total_issues = len(res["consolidated_issues"])
        final_val = res["final_validation"]

        # Results Summary Header
        st.markdown(f"### 📊 YOUR CODE REVIEW")
        st.markdown(
            f"<p style='color:#94A3B8; font-size:1rem;'><b>{total_issues} issue(s) found</b> that deserve attention.</p>",
            unsafe_allow_html=True
        )

        # Compact Metric Pills
        st.markdown(
            f"""
            <div class="metric-pill-container">
                <div class="metric-pill"><div class="metric-pill-num" style="color:#EF4444;">{get_count('CRITICAL')}</div><div class="metric-pill-lbl">Critical</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#F97316;">{get_count('HIGH')}</div><div class="metric-pill-lbl">High</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#F59E0B;">{get_count('MEDIUM')}</div><div class="metric-pill-lbl">Medium</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#10B981;">{get_count('LOW')}</div><div class="metric-pill-lbl">Low</div></div>
                <div class="metric-pill"><div class="metric-pill-num" style="color:#C084FC;">{res['total_iterations']}</div><div class="metric-pill-lbl">Iterations</div></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Validation Verdict Status Callout
        if final_val:
            if res["is_resolved"]:
                st.markdown(
                    f"""
                    <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); padding: 14px 20px; border-radius: 10px; margin-bottom: 20px; color: #34D399; font-weight: 600;">
                        ✓ PASSED AI RE-REVIEW — All detected issues resolved in {res['total_iterations']} iteration(s).
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); padding: 14px 20px; border-radius: 10px; margin-bottom: 20px; color: #FCA5A5; font-weight: 600;">
                        ⚠️ ISSUES REMAINING — {len(final_val.remaining_issues)} issue(s) persist after {res['total_iterations']} iteration(s).
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # Main Results Tabs
        tab_rev_overview, tab_rev_issues, tab_rev_fix, tab_rev_val = st.tabs([
            "📊 Architectural Overview",
            "🐞 Detected Issues & Audit",
            "✨ AI Fix & Code Comparison",
            "🔄 Self-Review & Validation History"
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
                    <div class="card-box" style="text-align:center; padding:30px;">
                        <div style="font-size:1.8rem;">✨ Looks good!</div>
                        <div style="color:#94A3B8; margin-top:6px;">No issues were detected by the configured review pipeline.</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                cat_filter = st.radio("Category Filter", options=["All", "Logic Bug", "Security Vulnerability", "Code Quality"], horizontal=True)
                
                filtered_issues = issues
                if cat_filter != "All":
                    filtered_issues = [i for i in issues if i.category == cat_filter]

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
                            <p style="margin: 8px 0 6px 0; color: #CBD5E1;"><b>Problem:</b> {iss.description}</p>
                            <div class="section-label label-why">Why it matters</div>
                            <p style="margin-bottom: 6px; color: #FCA5A5; font-size: 0.9rem;">{iss.impact}</p>
                            <div class="section-label label-rec">Recommended Fix</div>
                            <p style="margin-bottom: 6px; color: #6EE7B7; font-size: 0.9rem;">{iss.recommendation}</p>
                            {f"<pre style='background:#0B0F19; padding:8px; border-radius:6px; margin-top:8px; font-size:0.85rem;'>{iss.evidence}</pre>" if iss.evidence else ""}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        # TAB 3: AI FIX & COMPARISON
        with tab_rev_fix:
            st.markdown("### ✨ AI FIX")
            st.markdown("<p style='color:#94A3B8;'>CodeGuard found the problems. Here is a safer, corrected version.</p>", unsafe_allow_html=True)

            fixed_code = res["final_fixed_code"]
            
            c_orig, c_fix = st.columns(2)
            with c_orig:
                st.markdown("##### 🔴 Original Code")
                st.code(res["original_code"], language=language, line_numbers=True)
            with c_fix:
                st.markdown("##### 🟢 Fixed Code")
                st.code(fixed_code, language=language, line_numbers=True)

            st.markdown("##### 📜 Unified Git Diff")
            diff_text = generate_unified_diff(res["original_code"], fixed_code)
            if diff_text:
                st.code(diff_text, language="diff")
            else:
                st.info("No line changes detected between original and fixed code.")

        # TAB 4: SELF-REVIEW & VALIDATION HISTORY
        with tab_rev_val:
            st.markdown("### 🔄 SELF-REVIEW HISTORY")
            st.caption("Visualizing the agentic validation loop: Code → Review → Fix → Re-Review → Verdict")

            iterations = res["iterations"]
            if not iterations:
                st.info("Original code passed review with 0 required fixing cycles.")
            else:
                for it in iterations:
                    val = it.validation_result
                    icon = "🟢" if val.validation_status == "PASSED AI RE-REVIEW" else "🟠"
                    with st.expander(f"{icon} Iteration {it.iteration_number} — Status: {val.validation_status}", expanded=(it.iteration_number == len(iterations))):
                        st.write(f"**Verdict Explanation:** {val.summary}")

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
            st.caption("ℹ️ **Validation Disclaimer**: AI validation performs automated static re-analysis and neural re-review checks. It does not constitute mathematical formal verification.")
else:
    # Pre-Analysis Friendly Empty State
    st.markdown(
        """
        <div class="card-box" style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 1.4rem; font-weight: 700; color: #F1F5F9; margin-bottom: 8px;">
                Your code review starts here.
            </div>
            <div style="font-size: 0.95rem; color: #94A3B8;">
                Paste your code above or select one of our sample buttons to run static analysis and multi-agent review.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

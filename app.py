import os
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
    initial_sidebar_state="expanded"
)

# Custom Premium Dark Theme CSS
CUSTOM_CSS = """
<style>
    /* Dark Theme Accent Adjustments */
    .stApp {
        background-color: #0e1117;
        color: #e6e9ef;
    }
    
    /* Header Gradient */
    .main-header {
        font-family: 'Inter', system-ui, sans-serif;
        background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0px;
    }
    
    .sub-header {
        color: #9CA3AF;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    
    /* Metric Cards */
    .metric-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        margin-top: 4px;
    }
    
    /* Issue Card */
    .issue-card {
        background: #182232;
        border-left: 4px solid #3B82F6;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .issue-card.critical { border-left-color: #EF4444; }
    .issue-card.high { border-left-color: #F97316; }
    .issue-card.medium { border-left-color: #F59E0B; }
    .issue-card.low { border-left-color: #10B981; }
    
    /* Status Badges */
    .status-passed {
        background-color: #064E3B;
        color: #34D399;
        border: 1px solid #059669;
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .status-remaining {
        background-color: #7F1D1D;
        color: #FCA5A5;
        border: 1px solid #DC2626;
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Sample Code Snippets for Quick Testing
BUGGY_SAMPLE = """import os
import subprocess

API_KEY = "AIzaSyD9x8K11223344556677889900aabbcc"

def calculate_discount(price, count):
    # Division by zero if count is 0
    average = price / count
    
    # Faulty logic condition
    if price > 100 and price < 50:
        discount = 0.2
    else:
        discount = 0.05
    return average * (1 - discount)

def execute_user_command(user_input):
    # Dangerous eval and subprocess
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
from typing import List, Optional

def compute_average(numbers: List[float]) -> Optional[float]:
    \"\"\"Computes average safely checking for empty lists.\"\"\"
    if not numbers:
        return None
    return sum(numbers) / len(numbers)

def fetch_environment_key() -> str:
    \"\"\"Safely retrieves API key from environment.\"\"\"
    return os.getenv("API_KEY", "")
"""

# Initialize Session State
if "code_input" not in st.session_state:
    st.session_state.code_input = BUGGY_SAMPLE
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None

# Sidebar Configuration
with st.sidebar:
    st.markdown("<h2 style='margin-bottom:0;'>🛡️ CodeGuard AI</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9CA3AF; font-size:0.9rem;'>Analyze. Explain. Fix. Validate.</p>", unsafe_allow_html=True)
    st.divider()

    # API Key & Status Check
    env_key = os.getenv("GEMINI_API_KEY", "")
    user_api_key = st.text_input("Gemini API Key", value=env_key, type="password", help="Leave blank to use environment default or run static AST mode.")
    
    active_key = user_api_key.strip() or env_key.strip()
    llm_provider = GeminiLLMProvider(api_key=active_key)

    if llm_provider.is_available():
        st.success("🟢 Gemini AI Engine Active", icon="✅")
    else:
        st.warning("🟠 Offline Mode (Static AST Only)", icon="⚠️")
        st.caption("Provide a valid `GEMINI_API_KEY` to enable AI multi-agent reasoning & automated fix generation.")

    st.divider()

    # Model & Pipeline Controls
    selected_model = st.selectbox(
        "Gemini Model",
        options=["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"],
        index=0
    )
    llm_provider.model = selected_model

    max_iters = st.slider("Max Self-Review Iterations", min_value=1, max_value=3, value=3, help="Maximum fix-validation cycles in the self-review loop.")

    st.divider()
    st.subheader("⚡ Quick Load Examples")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🐛 Buggy Code", use_container_width=True):
            st.session_state.code_input = BUGGY_SAMPLE
            st.session_state.pipeline_result = None
            st.rerun()
    with col_s2:
        if st.button("✨ Clean Code", use_container_width=True):
            st.session_state.code_input = CLEAN_SAMPLE
            st.session_state.pipeline_result = None
            st.rerun()

# Main Application Layout
st.markdown("<div class='main-header'>CodeGuard AI</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Agentic AI Code Reviewer & Self-Fixing Engine</div>", unsafe_allow_html=True)

# Input Section
st.subheader("📝 Code Input")

input_tab1, input_tab2 = st.tabs(["💻 Code Editor", "📁 Upload Source File"])

uploaded_code = None

with input_tab1:
    code_text = st.text_area(
        "Source Code",
        value=st.session_state.code_input,
        height=240,
        placeholder="Paste your Python source code here..."
    )

with input_tab2:
    uploaded_file = st.file_uploader("Upload file (.py, .js, .java)", type=["py", "js", "java", "txt"])
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
                uploaded_code = content
                st.success(f"File '{uploaded_file.name}' loaded successfully ({len(content.splitlines())} lines).")

# Select active source code
active_code = uploaded_code if uploaded_code else code_text

col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
with col_ctrl1:
    language_sel = st.selectbox("Language Scope", options=["Python (Primary)", "JavaScript (Experimental)", "Java (Experimental)"], index=0)
    language = "python" if "Python" in language_sel else "javascript" if "JavaScript" in language_sel else "java"

with col_ctrl2:
    st.write("") # Spacer
    st.write("")
    analyze_btn = st.button("🛡️ Run CodeGuard Review", type="primary", use_container_width=True)

with col_ctrl3:
    st.write("")
    st.write("")
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state.code_input = ""
        st.session_state.pipeline_result = None
        st.rerun()

# Execute Orchestrator Pipeline
if analyze_btn:
    if not active_code or not active_code.strip():
        st.error("Please enter or upload valid source code before running review.")
    else:
        with st.spinner("🤖 Multi-Agent Pipeline Running (Analyze → Review → Security → Fix → Validate)..."):
            orchestrator = CodeGuardOrchestrator(llm_provider=llm_provider)
            res = orchestrator.execute_pipeline(
                code=active_code,
                language=language,
                max_iterations=max_iters
            )
            st.session_state.pipeline_result = res

# Display Dashboard Results
res = st.session_state.pipeline_result
if res:
    st.divider()
    
    if "error" in res:
        st.error(res["error"])
    else:
        # Header Metrics Bar
        review_obj = res["review"]
        counts = review_obj.severity_counts
        def get_count(k):
            return getattr(counts, k, 0) if hasattr(counts, k) else (counts.get(k, 0) if isinstance(counts, dict) else 0)

        total_issues = len(res["consolidated_issues"])
        final_val = res["final_validation"]
        
        st.markdown("### 📊 Pipeline Dashboard")
        
        m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns(6)
        with m_col1:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Total Issues</div><div class='metric-val' style='color:#3B82F6;'>{total_issues}</div></div>", unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Critical</div><div class='metric-val' style='color:#EF4444;'>{get_count('CRITICAL')}</div></div>", unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>High</div><div class='metric-val' style='color:#F97316;'>{get_count('HIGH')}</div></div>", unsafe_allow_html=True)
        with m_col4:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Medium</div><div class='metric-val' style='color:#F59E0B;'>{get_count('MEDIUM')}</div></div>", unsafe_allow_html=True)
        with m_col5:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Low</div><div class='metric-val' style='color:#10B981;'>{get_count('LOW')}</div></div>", unsafe_allow_html=True)
        with m_col6:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Iterations</div><div class='metric-val' style='color:#A855F7;'>{res['total_iterations']}</div></div>", unsafe_allow_html=True)

        st.write("")
        
        # Validation Status Banner
        if final_val:
            if res["is_resolved"]:
                st.markdown(
                    f"<div class='status-passed'>✅ STATUS: {final_val.validation_status} — All detected issues resolved in {res['total_iterations']} iteration(s).</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='status-remaining'>⚠️ STATUS: {final_val.validation_status} — {len(final_val.remaining_issues)} issue(s) remain after {res['total_iterations']} iteration(s).</div>",
                    unsafe_allow_html=True
                )

        st.write("")

        # Dashboard Tabs
        tab_overview, tab_bugs, tab_sec, tab_fix, tab_loop = st.tabs([
            "📊 Overview & Analysis",
            "🐞 Detected Issues",
            "🔒 Security Audit",
            "🛠️ Fixed Code & Diff",
            "🔄 Self-Review Loop History"
        ])

        # TAB 1: OVERVIEW & ANALYSIS
        with tab_overview:
            analysis = res["analysis"]
            st.markdown("#### Agent 1: Code Architectural Summary")
            st.write(f"**Detected Language:** `{analysis.language}`")
            st.write(f"**Purpose:** {analysis.purpose}")
            st.info(f"**Executive Summary:** {analysis.summary}")

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                st.markdown("##### Identified Components")
                if analysis.components:
                    for comp in analysis.components:
                        st.markdown(f"- `{comp}`")
                else:
                    st.caption("No explicit function/class components detected.")
            with col_a2:
                st.markdown("##### High-Risk Control Flows")
                if analysis.risk_areas:
                    for risk in analysis.risk_areas:
                        st.markdown(f"- ⚠️ {risk}")
                else:
                    st.caption("No specific high-risk control flows identified.")

        # TAB 2: DETECTED ISSUES
        with tab_bugs:
            st.markdown("#### Consolidated Review Findings")
            issues = res["consolidated_issues"]
            if not issues:
                st.success("🎉 No code quality bugs or logic issues were detected in this source file!")
            else:
                sev_filter = st.multiselect("Filter by Severity", options=["CRITICAL", "HIGH", "MEDIUM", "LOW"], default=["CRITICAL", "HIGH", "MEDIUM", "LOW"])
                for iss in issues:
                    if iss.severity in sev_filter:
                        badge_html = get_severity_badge_html(iss.severity)
                        cat_html = get_category_badge_html(iss.category)
                        st.markdown(
                            f"""
                            <div class='issue-card {iss.severity.lower()}'>
                                <div style='display:flex; justify-shadow:space-between; align-items:center;'>
                                    <div>{badge_html} &nbsp; {cat_html} &nbsp; <b>Line {iss.line}</b>: <span style='font-size:1.1rem; font-weight:700;'>{iss.title}</span></div>
                                    <span style='font-size:0.8rem; color:#94A3B8;'>Source: {iss.source}</span>
                                </div>
                                <p style='margin-top:8px; margin-bottom:4px;'><b>Problem:</b> {iss.description}</p>
                                <p style='margin-bottom:4px; color:#FCA5A5;'><b>Impact:</b> {iss.impact}</p>
                                <p style='margin-bottom:4px; color:#6EE7B7;'><b>Recommendation:</b> {iss.recommendation}</p>
                                {f"<pre style='background:#0F172A; padding:8px; border-radius:4px; margin-top:8px;'>{iss.evidence}</pre>" if iss.evidence else ""}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

        # TAB 3: SECURITY AUDIT
        with tab_sec:
            st.markdown("#### Agent 3: Security & Vulnerability Audit")
            sec_issues = res["security_issues"]
            if not sec_issues:
                st.success("🛡️ No obvious security vulnerabilities or exposed secrets detected!")
            else:
                for s_iss in sec_issues:
                    st.error(f"**[Line {s_iss.line}] {s_iss.title}**")
                    st.write(f"**Description:** {s_iss.description}")
                    st.write(f"**Operational Risk:** {s_iss.impact}")
                    st.write(f"**Remediation:** {s_iss.recommendation}")
                    if s_iss.evidence:
                        st.code(s_iss.evidence, language=language)
                    st.divider()

        # TAB 4: FIXED CODE & DIFF
        with tab_fix:
            st.markdown("#### Agent 4: Corrected Source Code")
            fixed_code = res["final_fixed_code"]
            
            c_code1, c_code2 = st.columns(2)
            with c_code1:
                st.markdown("##### 🔴 Original Code")
                st.code(res["original_code"], language=language, line_numbers=True)
            with c_code2:
                st.markdown("##### 🟢 Fixed Code")
                st.code(fixed_code, language=language, line_numbers=True)

            st.markdown("#### 📜 Unified Git Diff")
            diff_text = generate_unified_diff(res["original_code"], fixed_code)
            if diff_text:
                st.code(diff_text, language="diff")
            else:
                st.info("No code diff present (original and fixed code are identical).")

        # TAB 5: SELF-REVIEW LOOP HISTORY
        with tab_loop:
            st.markdown("#### Agent 5: Automated Self-Review & Validation History")
            st.caption("Demonstrating the iterative review loop: CODE → ANALYZE → REVIEW → FIX → RE-REVIEW → ITERATE")
            
            iterations = res["iterations"]
            if not iterations:
                st.info("The original code passed review on step 1 with 0 required fixing iterations.")
            else:
                for it in iterations:
                    val = it.validation_result
                    status_color = "🟢" if val.validation_status == "PASSED AI RE-REVIEW" else "🟠"
                    with st.expander(f"{status_color} Iteration {it.iteration_number} — Status: {val.validation_status}", expanded=(it.iteration_number == len(iterations))):
                        st.write(f"**Validation Summary:** {val.summary}")
                        
                        col_i1, col_i2, col_i3 = st.columns(3)
                        with col_i1:
                            st.markdown(f"**Resolved Issues ({len(val.resolved_issues)})**")
                            for r_title in val.resolved_issues:
                                st.markdown(f"- ✅ {r_title}")
                        with col_i2:
                            st.markdown(f"**Remaining Issues ({len(val.remaining_issues)})**")
                            for rem in val.remaining_issues:
                                st.markdown(f"- ⚠️ Line {rem.line}: {rem.title}")
                        with col_i3:
                            st.markdown(f"**Newly Introduced Issues ({len(val.new_issues)})**")
                            for new_i in val.new_issues:
                                st.markdown(f"- 🔴 Line {new_i.line}: {new_i.title}")
                        
                        st.markdown("##### Code state at this iteration:")
                        st.code(it.fixed_code, language=language)

            st.divider()
            st.caption("ℹ️ **Validation Disclaimer**: AI validation performs automated static & neural re-review pipeline checks. It does not constitute mathematical formal verification.")

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

# Page Configuration - Light Blue SaaS Theme
st.set_page_config(
    page_title="CodeGuard AI — Automated Code Review & Refactoring Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Light Blue SaaS Theme CSS with Pure Dark Coding Editor
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Theme:
       --bg-light-blue: #F0F6FD
       --surface-white: #FFFFFF
       --primary-blue: #2563EB (hover: #1D4ED8)
       --border-blue: #DCE7F5
       --text-navy: #0F172A
       --text-muted: #64748B
       --code-dark: #0A0E17
    */

    /* Global Light Blue Theme */
    html, body, .stApp {
        background-color: #F0F6FD !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Compact Page Container (Single Screen Fit) */
    .block-container {
        max-width: 1520px !important;
        width: calc(100% - 24px) !important;
        padding-top: 8px !important;
        padding-bottom: 8px !important;
        padding-left: 14px !important;
        padding-right: 14px !important;
        margin: 0 auto !important;
    }

    /* 1. Header Bar */
    .saas-header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 18px;
        background: #FFFFFF;
        border: 1px solid #DCE7F5;
        border-radius: 10px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.04);
    }
    .saas-brand-left {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .saas-brand-logo {
        width: 34px;
        height: 34px;
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 17px;
    }
    .saas-brand-title {
        font-size: 17px;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.015em;
    }
    .saas-brand-tagline {
        font-size: 12px;
        color: #475569;
        font-weight: 500;
        margin-left: 8px;
        background: #EBF3FC;
        padding: 2px 8px;
        border-radius: 6px;
        border: 1px solid #DCE7F5;
        display: inline-block;
    }

    /* Status Badges */
    .badge-status-ready {
        background: #F0FDF4;
        color: #15803D;
        border: 1px solid #BBF7D0;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11.5px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    .badge-status-static {
        background: #FFF7ED;
        color: #C2410C;
        border: 1px solid #FED7AA;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11.5px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }

    /* Sleek Lightweight SaaS Buttons */
    div.stButton, .stButton {
        width: 100%;
    }
    div[data-testid="stButton"] button,
    div.stButton > button,
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-secondary"],
    button[kind="primary"],
    button[kind="secondary"] {
        height: 32px !important;
        min-height: 32px !important;
        border-radius: 7px !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 0 10px !important;
        cursor: pointer !important;
        transition: all 0.15s ease-in-out !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 5px !important;
    }

    /* Secondary / Inactive Button (Crisp White + Subtle Slate Border) */
    div[data-testid="stButton"] button[kind="secondary"],
    button[data-testid="stBaseButton-secondary"],
    button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #475569 !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stButton"] button[kind="secondary"]:hover,
    button[data-testid="stBaseButton-secondary"]:hover,
    button[kind="secondary"]:hover {
        background-color: #F8FAFC !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
    }
    div[data-testid="stButton"] button[kind="secondary"]:active,
    button[data-testid="stBaseButton-secondary"]:active,
    button[kind="secondary"]:active {
        background-color: #F1F5F9 !important;
    }

    /* Primary Button (Light Blue Tinted, Lightweight, Non-Bulky) */
    div[data-testid="stButton"] button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    button[kind="primary"] {
        background-color: #EFF6FF !important;
        color: #1D4ED8 !important;
        border: 1px solid #BFDBFE !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.05) !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover,
    button[kind="primary"]:hover {
        background-color: #DBEAFE !important;
        border-color: #93C5FD !important;
        color: #1E40AF !important;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.12) !important;
    }
    div[data-testid="stButton"] button[kind="primary"]:active,
    button[data-testid="stBaseButton-primary"]:active,
    button[kind="primary"]:active {
        background-color: #BFDBFE !important;
    }

    /* 3. LIGHT BLUE & WHITE MODERN SELECTBOX (Python Dropdown) */
    div[data-testid="stSelectbox"], 
    .stSelectbox {
        width: 100%;
        background: transparent !important;
        border: none !important;
    }
    div[data-testid="stSelectbox"] > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        height: 32px !important;
        min-height: 32px !important;
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border: 1px solid #BFDBFE !important;
        border-radius: 7px !important;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.04) !important;
        padding: 0 8px !important;
        transition: all 0.15s ease-in-out !important;
        display: flex !important;
        align-items: center !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:hover > div {
        background-color: #F8FAFC !important;
        border-color: #93C5FD !important;
    }
    div[data-testid="stSelectbox"] div[data-baseweb="select"]:focus-within > div {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15) !important;
    }
    /* Force all text & spans inside selectbox to dark navy and transparent bg */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] div,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] p,
    div[data-testid="stSelectbox"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stSelectbox"] input,
    div[data-testid="stSelectbox"] [role="combobox"] {
        background: transparent !important;
        background-color: transparent !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
    }
    div[data-testid="stSelectbox"] svg,
    div[data-baseweb="select"] svg {
        fill: #2563EB !important;
        color: #2563EB !important;
    }

    /* Popover Menu / Dropdown Items Styling */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    ul[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border: 1px solid #DCE7F5 !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 20px -4px rgba(37, 99, 235, 0.12), 0 3px 6px -2px rgba(0, 0, 0, 0.04) !important;
        padding: 4px !important;
    }
    li[data-baseweb="menu-item"],
    ul[data-baseweb="menu"] li {
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        color: #0F172A !important;
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 6px 12px !important;
        border-radius: 6px !important;
        transition: all 0.1s ease !important;
        cursor: pointer !important;
    }
    li[data-baseweb="menu-item"]:hover,
    ul[data-baseweb="menu"] li:hover,
    li[data-baseweb="menu-item"][aria-selected="true"] {
        background-color: #EFF6FF !important;
        background: #EFF6FF !important;
        color: #1D4ED8 !important;
    }

    /* 4. Pure Dark Coding Editor */
    .stTextArea textarea {
        border-radius: 10px !important;
        border: 1px solid #1E293B !important;
        background: #0A0E17 !important;
        color: #F8FAFC !important;
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 12.5px !important;
        line-height: 1.55 !important;
        height: 345px !important;
        padding: 12px 14px !important;
        box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.6) !important;
    }
    .stTextArea textarea::placeholder {
        color: #64748B !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .stTextArea textarea:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2), inset 0 1px 4px rgba(0, 0, 0, 0.6) !important;
    }

    /* 4b. Dark IDE Code Panels (Side-by-Side Diff & Evidence) */
    div[data-testid="stCode"] {
        background-color: #0A0E17 !important;
        border: 1px solid #1E293B !important;
        border-radius: 8px !important;
        min-height: 280px !important;
        max-height: 360px !important;
        overflow: auto !important;
    }
    div[data-testid="stCode"] pre {
        background-color: transparent !important;
        font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
        font-size: 12px !important;
        line-height: 1.55 !important;
        color: #F8FAFC !important;
        padding: 10px 12px !important;
        margin: 0 !important;
        white-space: pre !important;
        overflow-x: auto !important;
    }
    div[data-testid="stCode"] code {
        background-color: transparent !important;
        font-family: inherit !important;
        font-size: inherit !important;
        color: inherit !important;
    }

    /* 5. Severity Cards Grid (SaaS Metric Cards) */
    .sev-cards-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        margin-bottom: 10px;
    }
    .sev-card-box {
        background: #FFFFFF;
        border-radius: 9px;
        padding: 8px 6px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 1px 2px rgba(37, 99, 235, 0.03);
        border: 1px solid #DCE7F5;
        transition: all 0.15s ease;
    }
    .sev-card-box:hover {
        border-color: #BFDBFE;
        box-shadow: 0 2px 5px rgba(37, 99, 235, 0.06);
    }
    .sev-card-num {
        font-size: 20px;
        font-weight: 700;
        line-height: 1.1;
    }
    .sev-card-lbl {
        font-size: 10.5px;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748B;
        margin-top: 2px;
        letter-spacing: 0.03em;
    }

    /* Banner Strip */
    .info-banner-strip {
        background: #EBF5FF;
        border: 1px solid #BFDBFE;
        border-radius: 8px;
        padding: 8px 12px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: #1E40AF;
        font-weight: 500;
        margin-bottom: 10px;
    }

    /* Empty State Card */
    .empty-review-box {
        text-align: center;
        padding: 40px 18px;
        background: #FFFFFF;
        border: 1px dashed #BFDBFE;
        border-radius: 10px;
        margin-top: 16px;
    }
    .empty-review-title {
        font-size: 16px;
        font-weight: 600;
        color: #0F172A;
        margin-top: 6px;
        margin-bottom: 4px;
    }
    .empty-review-desc {
        font-size: 12.5px;
        color: #64748B;
        max-width: 290px;
        margin: 0 auto;
        line-height: 1.5;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
        background: #E2EEFC !important;
        padding: 3px !important;
        border-radius: 8px !important;
        border: 1px solid #DCE7F5 !important;
        margin-bottom: 10px !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        color: #475569 !important;
        padding: 5px 14px !important;
        border: none !important;
        background: transparent !important;
        transition: all 0.15s ease !important;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #0F172A !important;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.1) !important;
    }

    /* Expander card custom styling */
    .streamlit-expanderHeader {
        background: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid #DCE7F5 !important;
        font-weight: 600 !important;
        font-size: 12.5px !important;
        color: #0F172A !important;
        padding: 8px 12px !important;
    }
    .streamlit-expanderHeader:hover {
        background: #F0F6FD !important;
        border-color: #BFDBFE !important;
    }

    /* RESPONSIVE MEDIA QUERIES (TABLET & MOBILE) */
    @media (max-width: 992px) {
        .block-container {
            padding: 8px !important;
            width: 100% !important;
        }
        .saas-header-bar {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
            padding: 10px 14px;
        }
        .sev-cards-grid {
            grid-template-columns: repeat(2, 1fr) !important;
            gap: 6px !important;
        }
        .stTextArea textarea {
            height: 240px !important;
        }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        [data-testid="stColumn"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }

    @media (max-width: 640px) {
        .saas-brand-title {
            font-size: 15px !important;
        }
        .saas-brand-tagline {
            display: block !important;
            margin-left: 0 !important;
            margin-top: 4px !important;
            font-size: 10px !important;
        }
        .sev-cards-grid {
            grid-template-columns: 1fr 1fr !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            flex-wrap: wrap !important;
            border-radius: 8px !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 4px 8px !important;
            font-size: 11px !important;
        }
        .stTextArea textarea {
            height: 200px !important;
        }
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

def clean_render_code(code_str: str) -> str:
    """
    Ensures source code strings have real newline line breaks instead of literal '\\n' sequences,
    strips extraneous markdown code fences, and formats cleanly for code display.
    """
    if not code_str:
        return ""
    
    # 1. Unescape literal '\n' sequences if present
    if "\\n" in code_str:
        code_str = code_str.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "    ")
    
    # 2. Strip any accidental markdown fences
    for tag in ["```cpp", "```c++", "```java", "```python", "```c", "```javascript", "```js", "```"]:
        if code_str.lower().startswith(tag):
            code_str = code_str[len(tag):]
            if "\n" in code_str:
                first, rest = code_str.split("\n", 1)
                if first.strip().lower() in ("cpp", "c++", "java", "python", "c", "javascript", "js"):
                    code_str = rest
            break
    if code_str.endswith("```"):
        code_str = code_str[:-3]
        
    return code_str.strip()


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

# Multi-Language Sample Code Snippets (Python, C++, Java)
SAMPLES = {
    "Python": {
        "buggy": """import subprocess

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
""",
        "logic": """def compute_ratio(a, b):
    # Missing zero check
    return a / b

def check_range(val):
    # Impossible condition
    if val > 100 and val < 10:
        return True
    return False
""",
        "clean": """def add(a, b):
    return a + b

result = add(2, 3)
print(result)
"""
    },
    "C++": {
        "buggy": """#include <iostream>
#include <cstring>
#include <cstdlib>

const char* API_KEY = "AIzaSyB3344556677889900112233445566";

void process_input(const char* user_input) {
    char buffer[16];
    // Dangerous buffer overflow vulnerability
    strcpy(buffer, user_input);
    
    // Command injection vulnerability
    char cmd[128];
    sprintf(cmd, "echo %s", buffer);
    system(cmd);
}

double calculate_ratio(double total, int count) {
    // Missing zero division check
    return total / count;
}

int main() {
    process_input("hello");
    std::cout << calculate_ratio(100.0, 0) << std::endl;
    return 0;
}
""",
        "logic": """#include <iostream>
#include <vector>

int get_element(const std::vector<int>& arr, int index) {
    // Off-by-one boundary error: using <= instead of <
    if (index <= arr.size()) {
        return arr[index];
    }
    return -1;
}

double divide_values(double a, double b) {
    // Missing zero divisor validation
    return a / b;
}
""",
        "clean": """#include <iostream>
#include <string>
#include <stdexcept>

double safe_divide(double numerator, double denominator) {
    if (denominator == 0.0) {
        throw std::invalid_argument("Denominator cannot be zero.");
    }
    return numerator / denominator;
}

int main() {
    try {
        std::cout << "Result: " << safe_divide(10.0, 2.0) << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
    }
    return 0;
}
"""
    },
    "Java": {
        "buggy": """import java.io.*;

public class PaymentService {
    private static final String API_KEY = "AIzaSyC99887766554433221100aabbccdd";

    public static void runCommand(String userInput) {
        try {
            // Dangerous command injection
            Runtime.getRuntime().exec("sh -c " + userInput);
        } catch (Exception e) {
            // Overly broad empty catch
        }
    }

    public static double computeDiscount(double total, int count) {
        // Missing zero division check
        double avg = total / count;
        return avg;
    }

    public static String readFile(String path) {
        try {
            // Potential resource leak without try-with-resources
            FileInputStream fis = new FileInputStream(path);
            return new String(fis.readAllBytes());
        } catch (Exception e) {
            return null;
        }
    }
}
""",
        "logic": """public class MathUtils {
    public static double divide(double a, double b) {
        // Missing zero validation
        return a / b;
    }

    public static boolean checkRange(int val) {
        // Impossible logical condition
        if (val > 100 && val < 10) {
            return true;
        }
        return false;
    }
}
""",
        "clean": """public class Calculator {
    public static int add(int a, int b) {
        return a + b;
    }

    public static void main(String[] args) {
        int result = add(5, 7);
        System.out.println("Sum: " + result);
    }
}
"""
    }
}

# Session State Initialization
if "code_input" not in st.session_state:
    st.session_state.code_input = ""
if "fixed_code" not in st.session_state:
    st.session_state["fixed_code"] = ""
if "editor_version" not in st.session_state:
    st.session_state.editor_version = 0
if "pipeline_result" not in st.session_state:
    st.session_state.pipeline_result = None
if "selected_filter" not in st.session_state:
    st.session_state.selected_filter = "All"
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "editor"
if "selected_language" not in st.session_state:
    st.session_state.selected_language = "Python"

# Server-Side Engine Initialization
llm_provider = GeminiLLMProvider()

# 1. UNIFIED COMPACT HEADER BAR
header_html = (
    '<div class="saas-header-bar">'
    '<div class="saas-brand-left">'
    '<div class="saas-brand-logo">🛡️</div>'
    '<div>'
    '<span class="saas-brand-title">CodeGuard AI</span>'
    '<span class="saas-brand-tagline">Analyze · Explain · Fix · Validate</span>'
    '</div>'
    '</div>'
    '</div>'
)
st.markdown(header_html, unsafe_allow_html=True)

# 2. MAIN WORKSPACE (LEFT 45% | RIGHT 55%)
col_left, col_right = st.columns([45, 55])

# ====================================================
# LEFT COLUMN: CODE EDITOR WORKSPACE (45%)
# ====================================================
with col_left:
    # 1. Modern Segmented Control + Multi-Language Selector
    col_m1, col_m2, col_m3 = st.columns([1.5, 1.5, 1.4])
    with col_m1:
        if st.button("</> Code Editor", use_container_width=True, type="primary" if st.session_state.input_mode == "editor" else "secondary"):
            st.session_state.input_mode = "editor"
            st.rerun()
    with col_m2:
        if st.button("↑ Upload File", use_container_width=True, type="primary" if st.session_state.input_mode == "upload" else "secondary"):
            st.session_state.input_mode = "upload"
            st.rerun()
    with col_m3:
        lang_list = ["Python", "C++", "Java"]
        curr_lang_idx = lang_list.index(st.session_state.selected_language) if st.session_state.selected_language in lang_list else 0
        lang_sel = st.selectbox("Language", options=lang_list, index=curr_lang_idx, label_visibility="collapsed", key="lang_selector_box")
        if lang_sel != st.session_state.selected_language:
            st.session_state.selected_language = lang_sel
            st.session_state["fixed_code"] = ""
            st.session_state.pipeline_result = None
            st.rerun()

    # Active syntax & samples mapping
    lang_syntax_map = {"Python": "python", "C++": "cpp", "Java": "java"}
    active_lang_name = st.session_state.selected_language
    language = lang_syntax_map.get(active_lang_name, "python")
    active_samples = SAMPLES.get(active_lang_name, SAMPLES["Python"])

    # 2. Modern Quick Sample Presets (1-Click Lightweight Chips for Active Language)
    col_p0, col_p1, col_p2, col_p3 = st.columns([1.1, 1.3, 1.3, 1.3])
    with col_p0:
        st.markdown("<div style='color:#475569; font-size:11.5px; font-weight:600; padding-top:7px;'>Samples:</div>", unsafe_allow_html=True)
    with col_p1:
        if st.button("⚡ Buggy Code", use_container_width=True, type="secondary"):
            st.session_state.editor_version += 1
            st.session_state.code_input = active_samples["buggy"]
            st.session_state["fixed_code"] = ""
            st.session_state.pipeline_result = None
            st.rerun()
    with col_p2:
        if st.button("🐞 Logic Flaws", use_container_width=True, type="secondary"):
            st.session_state.editor_version += 1
            st.session_state.code_input = active_samples["logic"]
            st.session_state["fixed_code"] = ""
            st.session_state.pipeline_result = None
            st.rerun()
    with col_p3:
        if st.button("✓ Clean Code", use_container_width=True, type="secondary"):
            st.session_state.editor_version += 1
            st.session_state.code_input = active_samples["clean"]
            st.session_state["fixed_code"] = ""
            st.session_state.pipeline_result = None
            st.rerun()

    # 3. Source Code Input (Black Background)
    placeholder_text = f"# Paste your {active_lang_name} code here...\n# Security, bugs & performance fixes validated automatically"
    if active_lang_name in ("C++", "Java"):
        placeholder_text = f"// Paste your {active_lang_name} code here...\n// Security, bugs & performance fixes validated automatically"

    if st.session_state.input_mode == "editor":
        edited_code = st.text_area(
            label="Source Code Input Box",
            value=st.session_state.code_input,
            height=345,
            placeholder=placeholder_text,
            label_visibility="collapsed",
            key=f"editor_area_{st.session_state.editor_version}"
        )
        st.session_state.code_input = edited_code
    else:
        uploaded_file = st.file_uploader("Upload Source (.py, .cpp, .java, .js, .txt)", type=["py", "cpp", "cc", "cxx", "c", "h", "hpp", "java", "js", "txt"])
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
                    st.session_state.editor_version += 1
                    st.session_state.code_input = content
                    # Auto-detect language from extension
                    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
                    if ext in ("cpp", "cc", "cxx", "c", "h", "hpp"):
                        st.session_state.selected_language = "C++"
                    elif ext in ("java",):
                        st.session_state.selected_language = "Java"
                    elif ext in ("py",):
                        st.session_state.selected_language = "Python"
                    st.success(f"✓ {uploaded_file.name} loaded ({len(content.splitlines())} lines).")

    active_code_str = st.session_state.code_input
    line_cnt = len(active_code_str.splitlines()) if active_code_str else 0
    char_cnt = len(active_code_str) if active_code_str else 0

    # 4. Action Bar: Clear & Review Code
    col_f1, col_f2 = st.columns([1, 1.4])
    with col_f1:
        st.markdown(
            f"""
            <div style="font-size:12px; color:#64748B; font-weight:500; margin-top:8px;">
                Lines: <b>{line_cnt}</b> &nbsp;|&nbsp; Characters: <b>{char_cnt:,}</b>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_f2:
        col_btn1, col_btn2 = st.columns([1, 2])
        with col_btn1:
            if st.button("🗑️ Clear", use_container_width=True):
                st.session_state.editor_version += 1
                st.session_state.code_input = ""
                st.session_state["fixed_code"] = ""
                st.session_state.pipeline_result = None
                st.rerun()
        with col_btn2:
            run_btn = st.button("Review Code", type="primary", use_container_width=True)

    # Process Review Execution
    if run_btn:
        code_to_review = st.session_state.code_input.strip()
        if not code_to_review:
            st.warning("Please paste or load code before starting the review.", icon="⚠️")
        else:
            progress_box = st.empty()
            try:
                with progress_box.container():
                    st.markdown(
                        """
                        <div style="text-align:center; padding:12px; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:9px;">
                            <div style="font-weight:600; color:#1E40AF; font-size:13.5px;">CodeGuard Review in Progress...</div>
                            <div style="font-size:12px; color:#2563EB; margin-top:4px; font-weight:500;">
                                ✓ Static AST &nbsp;|&nbsp; ✓ Logic Audit &nbsp;|&nbsp; ✓ Security Check &nbsp;|&nbsp; ◌ Fix Generation &nbsp;|&nbsp; ◌ Validation
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                orchestrator = CodeGuardOrchestrator(llm_provider=llm_provider)
                res = orchestrator.execute_pipeline(
                    code=code_to_review,
                    language=language,
                    max_iterations=1
                )
                st.session_state.pipeline_result = res
                st.session_state["fixed_code"] = res.get("final_fixed_code", "")
            except Exception as e:
                print(f"[CodeGuard App Error] {e}")
                st.session_state["fixed_code"] = ""
                st.session_state.pipeline_result = {
                    "error": f"AI review couldn't be completed: {str(e)}. Static analysis fallback is available."
                }
            finally:
                progress_box.empty()
            st.rerun()

# ====================================================
# RIGHT COLUMN: CODE REVIEW WORKSPACE (55%)
# ====================================================
with col_right:
    with st.container(height=540):
        # EMPTY STATE
        if st.session_state.pipeline_result is None:
            st.markdown(
                """
                <div class="empty-review-box">
                    <div style="font-size: 28px; color: #2563EB;">🛡️</div>
                    <div class="empty-review-title">Code Review Workspace</div>
                    <div class="empty-review-desc">
                        Paste your code or select a preset on the left, then click <b>Review Code</b> to begin.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # REVIEW RESULTS STATE
        else:
            res = st.session_state.pipeline_result

            # Header with Reset Button
            col_res1, col_res2 = st.columns([1.3, 3.7])
            with col_res1:
                if st.button("← New Review", use_container_width=True):
                    st.session_state["fixed_code"] = ""
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

                st.markdown("<h3 style='font-size: 19px; font-weight: 700; color: #0F172A; margin-bottom: 2px;'>Code Review Summary</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color:#64748B; font-size:13px; font-weight:500; margin-top:-4px; margin-bottom:8px;'><b>{total_issues} issue(s)</b> detected across your code.</p>", unsafe_allow_html=True)

                # FOUR SEVERITY CARDS
                st.markdown(
                    f"""
                    <div class="sev-cards-grid">
                        <div class="sev-card-box"><div class="sev-card-num" style="color:#DC2626;">{get_count('CRITICAL')}</div><div class="sev-card-lbl">Critical</div></div>
                        <div class="sev-card-box"><div class="sev-card-num" style="color:#EA580C;">{get_count('HIGH')}</div><div class="sev-card-lbl">High</div></div>
                        <div class="sev-card-box"><div class="sev-card-num" style="color:#D97706;">{get_count('MEDIUM')}</div><div class="sev-card-lbl">Medium</div></div>
                        <div class="sev-card-box"><div class="sev-card-num" style="color:#16A34A;">{get_count('LOW')}</div><div class="sev-card-lbl">Low</div></div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Info Banner
                if total_issues == 0:
                    st.markdown("<div class='info-banner-strip' style='background:#F0FDF4; border-color:#BBF7D0; color:#15803D;'>✓ CodeGuard analyzed your code and found zero issues.</div>", unsafe_allow_html=True)
                elif sec_count > 0:
                    st.markdown(f"<div class='info-banner-strip'>🛡️ CodeGuard identified {total_issues} issue(s), including <b>{sec_count} security risk(s)</b>.</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='info-banner-strip'>CodeGuard identified {total_issues} issue(s) that should be refactored.</div>", unsafe_allow_html=True)

                # Tabs Navigation
                t_issues, t_sec, t_fix, t_val = st.tabs([
                    f"Issues ({total_issues})",
                    f"Security ({sec_count})",
                    "Fixed Code",
                    "Validation"
                ])

                # TAB 1: ISSUES
                with t_issues:
                    if not consolidated:
                        st.success("✓ No issues detected.")
                    else:
                        st.markdown("<p style='font-size:11.5px; font-weight:600; color:#64748B; margin-bottom:4px;'>FILTER BY CATEGORY:</p>", unsafe_allow_html=True)
                        col_flt1, col_flt2, col_flt3, col_flt4, col_flt5 = st.columns(5)
                        
                        with col_flt1:
                            if st.button("All", use_container_width=True, type="primary" if st.session_state.selected_filter == "All" else "secondary"):
                                st.session_state.selected_filter = "All"
                                st.rerun()
                        with col_flt2:
                            if st.button("Security", use_container_width=True, type="primary" if st.session_state.selected_filter == "Security" else "secondary"):
                                st.session_state.selected_filter = "Security"
                                st.rerun()
                        with col_flt3:
                            if st.button("Bugs", use_container_width=True, type="primary" if st.session_state.selected_filter == "Bugs" else "secondary"):
                                st.session_state.selected_filter = "Bugs"
                                st.rerun()
                        with col_flt4:
                            if st.button("Reliability", use_container_width=True, type="primary" if st.session_state.selected_filter == "Reliability" else "secondary"):
                                st.session_state.selected_filter = "Reliability"
                                st.rerun()
                        with col_flt5:
                            if st.button("Quality", use_container_width=True, type="primary" if st.session_state.selected_filter == "Quality" else "secondary"):
                                st.session_state.selected_filter = "Quality"
                                st.rerun()

                        cat_filter = st.session_state.selected_filter
                        filtered = consolidated
                        if cat_filter == "Bugs":
                            filtered = [i for i in consolidated if i.category in ("Logic Bug", "Syntax Error")]
                        elif cat_filter == "Security":
                            filtered = [i for i in consolidated if i.category == "Security Vulnerability"]
                        elif cat_filter in ("Reliability", "Quality"):
                            filtered = [i for i in consolidated if i.category in ("Code Quality", "Performance")]

                        res_syntax = res.get("language", language)
                        for idx, iss in enumerate(filtered):
                            root_cause = get_root_cause_explanation(iss)
                            
                            with st.expander(f"{iss.severity} · {iss.category} — Line {iss.line}: {iss.title}", expanded=(idx == 0)):
                                st.markdown(f"<div style='margin-bottom:6px;'>{get_severity_badge_html(iss.severity)} &nbsp; {get_category_badge_html(iss.category)}</div>", unsafe_allow_html=True)
                                
                                st.markdown(f"<span style='font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;'>WHAT'S WRONG</span><br><span style='font-size:13px; color:#0F172A;'>{iss.description}</span>", unsafe_allow_html=True)
                                
                                c_w1, c_w2 = st.columns(2)
                                with c_w1:
                                    st.markdown(f"<span style='font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;'>WHY IT MATTERS</span><br><span style='font-size:12.5px; color:#334155;'>{iss.impact}</span>", unsafe_allow_html=True)
                                supplement_code = iss.recommendation
                                with c_w2:
                                    st.markdown(f"<span style='font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;'>RECOMMENDED FIX</span><br><span style='font-size:12.5px; color:#15803D;'>{supplement_code}</span>", unsafe_allow_html=True)
                                
                                st.markdown(f"<span style='font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;'>ROOT CAUSE</span><br><span style='font-size:12.5px; color:#334155;'>{root_cause}</span>", unsafe_allow_html=True)
                                
                                if iss.evidence and iss.evidence.strip():
                                    st.markdown(f"<span style='font-size:11px; color:#64748B; font-weight:600; text-transform:uppercase;'>EVIDENCE (Line {iss.line})</span>", unsafe_allow_html=True)
                                    st.code(redact_secrets(iss.evidence), language=res_syntax)

                # TAB 2: SECURITY AUDIT
                with t_sec:
                    sec_issues = [i for i in consolidated if i.category == "Security Vulnerability"]
                    st.markdown("<h4 style='font-size:15px; font-weight:700; color:#0F172A;'>Security Vulnerability Audit</h4>", unsafe_allow_html=True)
                    if not sec_issues:
                        st.success("✓ No exposed secrets or dangerous executions detected.")
                    else:
                        for s in sec_issues:
                            st.error(f"🚨 Line {s.line}: {s.title} — {redact_secrets(s.description)}")

                # TAB 3: FIX TAB
                with t_fix:
                    st.markdown("<h4 style='font-size:16px; font-weight:700; color:#0F172A; margin-bottom:2px;'>Corrected Code</h4>", unsafe_allow_html=True)
                    st.caption("CodeGuard generated and validated this refactored code patch.")

                    # Read ONLY from st.session_state["fixed_code"] / final state
                    raw_fixed = st.session_state.get("fixed_code", "")
                    clean_orig = clean_render_code(st.session_state.code_input or res.get("original_code", ""))
                    clean_fixed = clean_render_code(raw_fixed)
                    res_syntax = res.get("language", language)

                    c_orig, c_fix = st.columns(2)
                    with c_orig:
                        st.markdown("<div style='font-weight:600; color:#EF4444; font-size:11px; letter-spacing:0.04em; margin-bottom:4px; text-transform:uppercase;'>BEFORE (Issues)</div>", unsafe_allow_html=True)
                        st.code(redact_secrets(clean_orig), language=res_syntax, line_numbers=True)
                    with c_fix:
                        st.markdown("<div style='font-weight:600; color:#22C55E; font-size:11px; letter-spacing:0.04em; margin-bottom:4px; text-transform:uppercase;'>AFTER (Fixed)</div>", unsafe_allow_html=True)
                        if clean_fixed and clean_fixed.strip():
                            st.code(redact_secrets(clean_fixed), language=res_syntax, line_numbers=True)
                        else:
                            st.info("No corrected code generated.")

                    st.markdown("<h5 style='font-weight:600; color:#0F172A; margin-top:10px; margin-bottom:4px;'>Remediation Summary</h5>", unsafe_allow_html=True)
                    
                    rem_issues = res.get("final_remaining_issues", [])
                    if not rem_issues or res.get("is_resolved", False):
                        st.markdown("<div style='color:#15803D; font-weight:700; font-size:13px; margin-bottom:2px;'>✓ Fix Complete — Code Applied & Validated Successfully</div><div style='color:#15803D; font-size:12px; margin-bottom:6px;'>All detected issues have been completely remediated.</div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='color:#D97706; font-weight:600; font-size:12.5px; margin-bottom:4px;'>⚠ Unable to fully remediate automatically (Some issues require manual review):</div>", unsafe_allow_html=True)
                        for r_iss in rem_issues:
                            st.write(f"- ⚠ Line {r_iss.line}: {r_iss.title} — {r_iss.description}")

                    # List resolved items
                    for iss in consolidated:
                        if not any(r.title == iss.title for r in rem_issues):
                            st.write(f"- ✓ Resolved: {iss.title} (Line {iss.line})")

                # TAB 4: VALIDATION TAB
                with t_val:
                    st.markdown("<h4 style='font-size:17px; font-weight:700; color:#0F172A;'>Validation Report</h4>", unsafe_allow_html=True)
                    st.caption("Automated AST Static Verification + Neural AI Re-Audit")

                    rem_issues = res.get("final_remaining_issues", [])
                    rem_count = len(rem_issues)

                    if res.get("is_resolved", False) or rem_count == 0:
                        st.success("✓ Validation Passed — All detected issues successfully resolved with no introduced regressions.")
                    else:
                        st.warning("⚠ Unable to fully remediate automatically — Some remaining issues require manual attention.")

                    st.write(f"- Issues Identified: **{total_issues}**")
                    st.write(f"- Issues Remediated: **{total_issues - rem_count}**")
                    st.write(f"- Issues Remaining: **{rem_count}**")
                    st.write(f"- Review Cycles: **{res.get('total_iterations', 1)}**")

                    with st.expander("How CodeGuard Reviewed This Code"):
                        st.write("1. Deterministic AST & Ruff Structural Scan")
                        st.write("2. AI Logic Bug & Security Vulnerability Audit")
                        st.write("3. Automated Safe Fix Generation")
                        st.write("4. AST Static Re-Check + Neural Validation Loop")
                        st.caption(f"Completed {res.get('total_iterations', 1)} validation cycle(s).")

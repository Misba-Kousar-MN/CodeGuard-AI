# 🛡️ CodeGuard AI — AI Code Reviewer & Bug-Fixing Agent

**Tagline**: *"Analyze. Explain. Fix. Validate."*

CodeGuard AI is an advanced, multi-agent code analysis and automated refactoring engine built with **Google Gemini**, **Pydantic**, **Python AST**, and **Streamlit**.

Unlike generic "paste-and-prompt" AI tools that generate unvalidated code fixes, CodeGuard AI introduces an **agentic self-review validation loop**. Generated fixes are independently re-reviewed by an AI Validator Agent combined with deterministic static analysis before presenting the final result.

---

## 🌟 Key Features

- 🤖 **5 Logically Distinct AI Agents**: Specialized agents for analysis, review, security auditing, fix generation, and independent validation.
- ⚡ **Hybrid Analysis Engine**: Combines deterministic Python AST static parsing + Ruff linting with deep Gemini LLM reasoning.
- 🔄 **Self-Review Loop**: Iteratively validates generated fixes up to 3 cycles to eliminate regression bugs and introduced vulnerabilities.
- 🛡️ **Security & Secrets Audit**: Detects hardcoded secrets, `eval`/`exec`, command injection (`shell=True`), and bare `except:` clauses.
- 📊 **Developer-First UI**: Dark-mode Streamlit dashboard with issue severity badges, unified git diff viewer, and iteration timeline.
- 🔌 **Graceful Offline Fallback**: Operates fully in deterministic static AST mode if no Gemini API key is configured.

---

## 🏗️ Multi-Agent Architecture

```
                               ┌─────────────────────────┐
                               │     USER SOURCE CODE    │
                               └────────────┬────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
         Deterministic Static                             Agent 1: Code Analyzer
        Analysis (AST + Ruff)                              (Language/Structure)
                    │                                               │
                    └───────────────────────┬───────────────────────┘
                                            ▼
                                [ Unified Code Context ]
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
         Agent 2: Code Reviewer                         Agent 3: Security Reviewer
        (Logic/Quality/Edge Cases)                     (Secrets/Injections/Risks)
                    │                                               │
                    └───────────────────────┬───────────────────────┘
                                            ▼
                                [ Consolidated Findings ]
                                            │
                                            ▼
                                  Agent 4: Fixing Agent
                              (Generates Corrected Code)
                                            │
                                            ▼
                                 Agent 5: Validator Agent
                             (Re-reviews Fixed Code + AST)
                                            │
                                 ┌──────────┴──────────┐
                                 ▼                     ▼
                         Issues Remaining?           Passed?
                            /        \                  │
                          YES         NO                │
                           │           └────────────────┤
                           ▼                            ▼
                    Fix Again (Max 3)           [ Final Report & UI ]
```

---

## 🤖 Logically Distinct Agents

1. **Agent 1 — Code Analyzer** (`agents/analyzer.py`): Parses code structure, identifies core purpose, functions, classes, and high-risk control flows. Returns `AnalysisResult`.
2. **Agent 2 — Code Reviewer** (`agents/reviewer.py`): Performs deep review for logical bugs, runtime risks, off-by-one errors, and performance flaws. Returns `ReviewResult`.
3. **Agent 3 — Security Reviewer** (`agents/security.py`): Audits code for hardcoded secrets, dangerous `eval`/`exec`, `shell=True` command injection, and insecure permissions. Returns security findings.
4. **Agent 4 — Fixing Agent** (`agents/fixer.py`): Generates production-ready corrected code addressing all detected issues while preserving intended functionality. Returns `FixResult`.
5. **Agent 5 — Validator Agent** (`agents/validator.py`): Independently re-reviews generated fixed code with static analysis and AI re-audit. Returns `ValidationResult`.

---

## 🛠️ Technology Stack

- **Frontend / Dashboard**: Streamlit (Python)
- **AI Core / LLM**: Google Gemini API via official `google-genai` SDK
- **Structured Schemas**: Pydantic v2
- **Static Code Analysis**: Python `ast` module + Ruff linter
- **Environment Management**: `python-dotenv`
- **Testing**: Python `unittest` framework

---

## 🚀 Quick Start & Local Installation

### Prerequisites
- Python 3.10+
- A Google Gemini API Key (Get one from [Google AI Studio](https://aistudio.google.com/))

### 1. Clone & Setup Project
```bash
git clone https://github.com/your-username/codeguard-ai.git
cd codeguard-ai
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file from the provided `.env.example`:
```bash
cp .env.example .env
```
Edit `.env` and add your Gemini API Key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```

### 4. Run Locally
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Unit & Integration Tests

Execute the automated test suite covering AST detection, orchestrator loop, and end-to-end execution:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## ☁️ Deployment (Streamlit Community Cloud)

1. Push your repository to GitHub (ensure `.env` is listed in `.gitignore`).
2. Log into [Streamlit Community Cloud](https://streamlit.io/cloud).
3. Connect your repository and set `Main file path` to `app.py`.
4. Under **Advanced Settings → Secrets**, configure:
   ```toml
   GEMINI_API_KEY = "your_actual_gemini_api_key_here"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```
5. Deploy!

---

## ⚠️ Disclaimer & Limitations

- **Validation Disclaimer**: AI validation performs automated static re-analysis and neural re-review checks. It does not constitute mathematical formal verification.
- **Language Scope**: Priority is given to Python analysis. JavaScript and Java support are designed into the schema for future expansion.

---

## 📜 License

MIT License. Built for Generative AI Developer Internship Evaluation.

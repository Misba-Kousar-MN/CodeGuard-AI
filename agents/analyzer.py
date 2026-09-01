import os
from typing import Optional
from core.llm import GeminiLLMProvider
from core.schemas import AnalysisResult

class CodeAnalyzerAgent:
    """Agent 1: Understands submitted source code structure, purpose, and key components."""

    def __init__(self, llm: GeminiLLMProvider):
        self.llm = llm
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "analyzer.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def analyze(self, code: str, language: str = "python") -> AnalysisResult:
        if not self.llm.is_available():
            # Fallback for offline mode without API key
            return AnalysisResult(
                language=language,
                purpose="Code Analysis (Offline Mode - Static Only)",
                components=["Unknown (LLM Unavailable)"],
                risk_areas=["AST Static Check Available Only"],
                summary="Gemini API Key is not configured. Running deterministic AST static analysis only."
            )

        prompt = self.prompt_template.replace("{code}", code).replace("{language}", language)
        result = self.llm.generate_structured(
            prompt=prompt,
            schema_class=AnalysisResult,
            system_instruction="You are Agent 1 (Code Analyzer). Analyze code structure and return JSON strictly following the AnalysisResult schema."
        )

        if not result:
            return AnalysisResult(
                language=language,
                purpose="Automated Code Parsing",
                components=["Parsed Module"],
                risk_areas=["Unverified"],
                summary="Analysis performed via static analysis. LLM response was unparseable."
            )
        return result

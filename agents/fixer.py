import os
from typing import List
from core.llm import GeminiLLMProvider
from core.schemas import ReviewIssue, FixResult

class FixingAgent:
    """Agent 4: Generates corrected source code addressing detected bugs and security vulnerabilities."""

    def __init__(self, llm: GeminiLLMProvider):
        self.llm = llm
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "fixer.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def generate_fix(self, code: str, issues: List[ReviewIssue], language: str = "python") -> FixResult:
        if not issues:
            return FixResult(
                fixed_code=code,
                changes_made=["No changes needed. No issues were detected in the source code."],
                explanation="Original code was analyzed and no critical or high severity bugs were identified."
            )

        issues_text = "\n".join([
            f"- [{iss.category}] Severity: {iss.severity} | Line {iss.line} | {iss.title}\n  Description: {iss.description}\n  Recommendation: {iss.recommendation}"
            for iss in issues
        ])

        if not self.llm.is_available():
            return FixResult(
                fixed_code=code,
                changes_made=["LLM Fix Unavailable (No Gemini API Key provided)"],
                explanation="Fix generation requires Gemini API Key. Static analysis detected issues but automated fix generation is offline."
            )

        prompt = self.prompt_template.format(
            code=code,
            language=language,
            issues_text=issues_text
        )

        result = self.llm.generate_structured(
            prompt=prompt,
            schema_class=FixResult,
            system_instruction="You are Agent 4 (Fixing Agent). Return complete fixed source code and explicit changes list strictly matching the FixResult schema."
        )

        if not result or not result.fixed_code.strip():
            return FixResult(
                fixed_code=code,
                changes_made=["Fix generation encountered parse error"],
                explanation="Failed to parse LLM structured fix output. Original code retained."
            )

        # Clean markdown code fence formatting if present inside fixed_code field
        cleaned_code = result.fixed_code.strip()
        if cleaned_code.startswith("```python"):
            cleaned_code = cleaned_code.split("```python")[1].split("```")[0].strip()
        elif cleaned_code.startswith("```"):
            cleaned_code = cleaned_code.split("```")[1].split("```")[0].strip()
        result.fixed_code = cleaned_code

        return result

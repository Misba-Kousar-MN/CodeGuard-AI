import os
from typing import List
from core.llm import GeminiLLMProvider
from core.schemas import ReviewIssue, ReviewResult, AnalysisResult

class CodeReviewerAgent:
    """Agent 2: Performs detailed code review detecting logical bugs, edge cases, quality and performance issues."""

    def __init__(self, llm: GeminiLLMProvider):
        self.llm = llm
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "reviewer.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def review(self, code: str, analysis: AnalysisResult, static_issues: List[ReviewIssue], language: str = "python") -> ReviewResult:
        static_str = "\n".join([f"- [Line {i.line}] {i.severity} {i.title}: {i.description}" for i in static_issues]) if static_issues else "None"

        if not self.llm.is_available():
            # Return static issues wrapped in ReviewResult
            counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for iss in static_issues:
                counts[iss.severity] = counts.get(iss.severity, 0) + 1
            return ReviewResult(
                summary="Deterministic AST Static Code Review (LLM Key Unavailable).",
                issues=static_issues,
                severity_counts=counts,
                overall_assessment="Static Analysis Complete."
            )

        prompt = self.prompt_template.format(
            code=code,
            language=language,
            analysis_summary=analysis.summary,
            static_issues=static_str
        )

        result = self.llm.generate_structured(
            prompt=prompt,
            schema_class=ReviewResult,
            system_instruction="You are Agent 2 (Code Reviewer). Review code for logical bugs and quality issues."
        )

        if not result:
            counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for iss in static_issues:
                counts[iss.severity] = counts.get(iss.severity, 0) + 1
            return ReviewResult(
                summary="AST Static Review completed. LLM review unavailable.",
                issues=static_issues,
                severity_counts=counts,
                overall_assessment="Partial Review Completed."
            )

        # Merge any static AST issues that might have been missed by LLM
        existing_keys = {(iss.line, iss.title) for iss in result.issues}
        for st_iss in static_issues:
            if (st_iss.line, st_iss.title) not in existing_keys:
                result.issues.append(st_iss)

        # Recalculate severity counts
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for iss in result.issues:
            counts[iss.severity] = counts.get(iss.severity, 0) + 1
        result.severity_counts = counts

        return result

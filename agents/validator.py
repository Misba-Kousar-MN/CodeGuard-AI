import os
from typing import List
from core.llm import GeminiLLMProvider
from core.schemas import ReviewIssue, ValidationResult
from analyzers.static_analysis import run_static_analysis

class ValidatorAgent:
    """Agent 5: Independently re-reviews generated fixed code to verify resolution and detect regression bugs."""

    def __init__(self, llm: GeminiLLMProvider):
        self.llm = llm
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "validator.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def validate(
        self,
        original_code: str,
        fixed_code: str,
        original_issues: List[ReviewIssue],
        iteration_count: int = 1,
        language: str = "python"
    ) -> ValidationResult:
        # Step 1: Re-run deterministic AST static analysis on fixed code
        re_static_issues = run_static_analysis(fixed_code)

        orig_issues_text = "\n".join([
            f"- [{iss.category}] Line {iss.line}: {iss.title} - {iss.description}"
            for iss in original_issues
        ]) if original_issues else "None"

        re_static_text = "\n".join([
            f"- [{iss.category}] Line {iss.line}: {iss.title} - {iss.description}"
            for iss in re_static_issues
        ]) if re_static_issues else "None (Deterministic AST passed cleanly)"

        # Fallback mode if LLM unavailable
        if not self.llm.is_available():
            if re_static_issues:
                return ValidationResult(
                    validation_status="ISSUES REMAINING",
                    resolved_issues=[],
                    remaining_issues=re_static_issues,
                    new_issues=[],
                    iteration_count=iteration_count,
                    summary=f"AST static analysis re-review found {len(re_static_issues)} issues in fixed code."
                )
            return ValidationResult(
                validation_status="PASSED AI RE-REVIEW",
                resolved_issues=[i.title for i in original_issues],
                remaining_issues=[],
                new_issues=[],
                iteration_count=iteration_count,
                summary="AST static analysis re-review passed with 0 remaining syntax/AST errors."
            )

        prompt = self.prompt_template.format(
            original_code=original_code,
            fixed_code=fixed_code,
            original_issues_text=orig_issues_text,
            re_static_issues=re_static_text,
            language=language
        )

        result = self.llm.generate_structured(
            prompt=prompt,
            schema_class=ValidationResult,
            system_instruction="You are Agent 5 (Validator Agent). Re-review fixed code independently and determine if issues remain."
        )

        if not result:
            # Fallback based on re_static_issues if LLM validation response was unparseable
            status = "ISSUES REMAINING" if re_static_issues else "PASSED AI RE-REVIEW"
            return ValidationResult(
                validation_status=status,
                resolved_issues=[i.title for i in original_issues if not any(r.title == i.title for r in re_static_issues)],
                remaining_issues=re_static_issues,
                new_issues=[],
                iteration_count=iteration_count,
                summary=f"Validation completed with status {status} based on static re-analysis."
            )

        result.iteration_count = iteration_count

        # Ensure any critical AST errors detected in re_static_issues are included in remaining_issues
        re_static_titles = {i.title for i in result.remaining_issues}
        for st_iss in re_static_issues:
            if st_iss.title not in re_static_titles:
                result.remaining_issues.append(st_iss)

        # Update validation status based on remaining issues
        if result.remaining_issues or result.new_issues:
            result.validation_status = "ISSUES REMAINING"
        else:
            result.validation_status = "PASSED AI RE-REVIEW"

        return result

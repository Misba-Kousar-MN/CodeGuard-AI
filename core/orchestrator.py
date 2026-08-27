from typing import List, Dict, Any, Optional
from core.llm import GeminiLLMProvider
from core.schemas import (
    AnalysisResult,
    ReviewIssue,
    ReviewResult,
    SeverityCounts,
    FixResult,
    ValidationResult,
    PipelineIteration
)
from analyzers.static_analysis import run_static_analysis
from analyzers.ruff_analyzer import run_ruff_analysis
from agents.analyzer import CodeAnalyzerAgent
from agents.reviewer import CodeReviewerAgent
from agents.security import SecurityReviewerAgent
from agents.fixer import FixingAgent
from agents.validator import ValidatorAgent


class CodeGuardOrchestrator:
    """
    Main Multi-Agent Workflow Orchestrator for CodeGuard AI.
    Executes the Hybrid Analysis + Self-Review Validation Loop.
    """

    def __init__(self, llm_provider: Optional[GeminiLLMProvider] = None):
        self.llm = llm_provider or GeminiLLMProvider()
        self.analyzer_agent = CodeAnalyzerAgent(self.llm)
        self.reviewer_agent = CodeReviewerAgent(self.llm)
        self.security_agent = SecurityReviewerAgent(self.llm)
        self.fixer_agent = FixingAgent(self.llm)
        self.validator_agent = ValidatorAgent(self.llm)

    def _consolidate_issues(self, issues: List[ReviewIssue]) -> List[ReviewIssue]:
        """
        Consolidates overlapping static + AI findings into distinct actionable issues.
        Merges duplicate or substantially overlapping findings on the same line/problem.
        """
        if not issues:
            return []

        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        
        def get_topic_key(iss: ReviewIssue) -> str:
            text = f"{iss.title} {iss.category} {iss.description}".lower()
            if "api_key" in text or "api key" in text or "secret" in text or "credential" in text:
                return "secret_key"
            if "eval" in text or "exec" in text or "dynamic code" in text:
                return "eval_exec"
            if "subprocess" in text or "shell=true" in text or "command injection" in text:
                return "subprocess_shell"
            if "zero" in text or "divide" in text or "division" in text:
                return "division_by_zero"
            if "except" in text or "catch-all" in text or "catch all" in text:
                return "bare_except"
            return iss.title.lower().strip()

        seen_groups: Dict[tuple, ReviewIssue] = {}

        for iss in issues:
            topic = get_topic_key(iss)
            group_key = (iss.line, topic)

            if group_key not in seen_groups:
                seen_groups[group_key] = iss
            else:
                existing = seen_groups[group_key]
                if severity_rank.get(iss.severity, 4) < severity_rank.get(existing.severity, 4):
                    seen_groups[group_key] = iss

        consolidated = list(seen_groups.values())
        consolidated.sort(key=lambda i: (severity_rank.get(i.severity, 4), i.line))
        return consolidated

    def execute_pipeline(
        self,
        code: str,
        language: str = "python",
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Executes the full CodeGuard AI pipeline:
        Analyze -> Review -> Security -> Fix -> Validate (Iterate up to max_iterations)
        """
        if not code or not code.strip():
            return {
                "error": "Empty code provided. Please upload or paste valid source code.",
                "is_resolved": False
            }

        # Step 1: Hybrid Deterministic Static Analysis (AST + Ruff)
        ast_issues = run_static_analysis(code)
        ruff_issues = run_ruff_analysis(code)
        
        # Deduplicate static issues
        static_issues: List[ReviewIssue] = []
        seen_keys = set()
        for iss in ast_issues + ruff_issues:
            key = (iss.line, iss.title)
            if key not in seen_keys:
                seen_keys.add(key)
                static_issues.append(iss)

        # Step 2: Agent 1 - Code Analyzer
        analysis = self.analyzer_agent.analyze(code, language=language)

        # Step 3: Agent 2 - Code Reviewer (Logic & Quality)
        code_review = self.reviewer_agent.review(
            code=code,
            analysis=analysis,
            static_issues=static_issues,
            language=language
        )

        # Step 4: Agent 3 - Security Reviewer
        security_issues = self.security_agent.audit(
            code=code,
            analysis=analysis,
            static_security_issues=static_issues,
            language=language
        )

        # Consolidate all detected issues (deduplicated & merged by line/topic)
        all_raw_issues = code_review.issues + security_issues + static_issues
        consolidated_issues = self._consolidate_issues(all_raw_issues)

        # Update severity counts
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for iss in consolidated_issues:
            severity_counts[iss.severity] = severity_counts.get(iss.severity, 0) + 1

        code_review.severity_counts = SeverityCounts(**severity_counts)

        # If no issues were found, code is already clean!
        if not consolidated_issues:
            clean_validation = ValidationResult(
                validation_status="PASSED AI RE-REVIEW",
                resolved_issues=[],
                remaining_issues=[],
                new_issues=[],
                iteration_count=0,
                summary="No remaining issues detected by the configured review pipeline."
            )
            return {
                "original_code": code,
                "analysis": analysis,
                "review": code_review,
                "security_issues": security_issues,
                "consolidated_issues": [],
                "iterations": [],
                "final_fixed_code": code,
                "final_validation": clean_validation,
                "total_iterations": 0,
                "is_resolved": True
            }

        # Step 5: Agent 4 & 5 - Self-Review Validation Loop (Fix -> Validate -> Iterate)
        current_code = code
        current_issues = consolidated_issues
        iterations: List[PipelineIteration] = []
        final_validation: Optional[ValidationResult] = None
        
        # Enforce max 3 iterations strict boundary
        loop_limit = min(max(1, max_iterations), 3)

        for iteration_idx in range(1, loop_limit + 1):
            # Agent 4: Generate Fix
            fix_res: FixResult = self.fixer_agent.generate_fix(
                code=current_code,
                issues=current_issues,
                language=language
            )

            # Agent 5: Validate Fixed Code
            val_res: ValidationResult = self.validator_agent.validate(
                original_code=current_code,
                fixed_code=fix_res.fixed_code,
                original_issues=current_issues,
                iteration_count=iteration_idx,
                language=language
            )

            # Record iteration
            iteration_record = PipelineIteration(
                iteration_number=iteration_idx,
                input_code=current_code,
                fixed_code=fix_res.fixed_code,
                issues_before=list(current_issues),
                validation_result=val_res
            )
            iterations.append(iteration_record)

            final_validation = val_res
            current_code = fix_res.fixed_code

            # Check loop termination condition
            if val_res.validation_status == "PASSED AI RE-REVIEW" or (not val_res.remaining_issues and not val_res.new_issues):
                break

            # Prepare issues for next iteration if needed
            current_issues = val_res.remaining_issues + val_res.new_issues

        is_resolved = (
            final_validation is not None and
            final_validation.validation_status == "PASSED AI RE-REVIEW"
        )

        return {
            "original_code": code,
            "analysis": analysis,
            "review": code_review,
            "security_issues": security_issues,
            "consolidated_issues": consolidated_issues,
            "iterations": iterations,
            "final_fixed_code": current_code,
            "final_validation": final_validation,
            "total_iterations": len(iterations),
            "is_resolved": is_resolved
        }

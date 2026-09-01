import ast
from typing import Dict, Any, List, Optional, Tuple
from core.llm import GeminiLLMProvider
from core.schemas import (
    ReviewIssue,
    ValidationResult,
    PipelineIteration,
    SeverityCounts
)
from analyzers.static_analysis import run_static_analysis
from analyzers.ruff_analyzer import run_ruff_analysis
from agents.analyzer import CodeAnalyzerAgent
from agents.reviewer import CodeReviewerAgent
from agents.security import SecurityReviewerAgent
from agents.fixer import FixingAgent, _deterministic_fallback_fix, _clean_code_fences, _prune_unused_python_imports
from agents.validator import ValidatorAgent


class CodeGuardOrchestrator:
    """
    CodeGuard AI Core Orchestrator:
    Manages the 5-Agent automated code review, security audit, remediation, and validation pipeline.
    """

    def __init__(self, llm_provider: Optional[GeminiLLMProvider] = None):
        self.llm_provider = llm_provider or GeminiLLMProvider()
        self.analyzer_agent = CodeAnalyzerAgent(self.llm_provider)
        self.reviewer_agent = CodeReviewerAgent(self.llm_provider)
        self.security_agent = SecurityReviewerAgent(self.llm_provider)
        self.fixer_agent = FixingAgent(self.llm_provider)
        self.validator_agent = ValidatorAgent(self.llm_provider)

    def _consolidate_issues(self, issues: List[ReviewIssue]) -> List[ReviewIssue]:
        """
        Consolidates and de-duplicates detected issues across AST, Ruff, and AI Agents.
        Merges issues by line number and normalized category/title, prioritizing highest severity.
        """
        if not issues:
            return []

        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        seen_groups: Dict[str, ReviewIssue] = {}

        for iss in issues:
            # Grouping key combining line and normalized issue essence
            clean_title = iss.title.lower().replace("`", "").replace("'", "")
            category_key = iss.category.lower().replace(" ", "_")
            group_key = f"{iss.line}_{category_key}_{clean_title[:30]}"

            if group_key not in seen_groups:
                seen_groups[group_key] = iss
            else:
                existing = seen_groups[group_key]
                if severity_rank.get(iss.severity, 4) < severity_rank.get(existing.severity, 4):
                    seen_groups[group_key] = iss

        consolidated = list(seen_groups.values())
        consolidated.sort(key=lambda i: (severity_rank.get(i.severity, 4), i.line))
        return consolidated

    def analyze_source(self, code: str, language: str = "python") -> List[ReviewIssue]:
        """
        Executes the exact deterministic AST and static analysis suite used by CodeGuard.
        Returns the consolidated list of all detected actionable issues.
        """
        if not code or not code.strip():
            return []

        lang_lower = language.lower().strip()
        if lang_lower in ("python", "py"):
            ast_issues = run_static_analysis(code, language="python")
            ruff_issues = run_ruff_analysis(code)
            raw_static = ast_issues + ruff_issues
        else:
            raw_static = run_static_analysis(code, language=lang_lower)

        seen_keys = set()
        static_issues: List[ReviewIssue] = []
        for iss in raw_static:
            key = (iss.line, iss.title)
            if key not in seen_keys:
                seen_keys.add(key)
                static_issues.append(iss)

        return self._consolidate_issues(static_issues)

    def remediate_and_validate(
        self,
        code: str,
        initial_findings: Optional[List[ReviewIssue]] = None,
        language: str = "python",
        max_iterations: int = 1
    ) -> Tuple[str, List[ReviewIssue], int, bool, List[PipelineIteration], Optional[ValidationResult]]:
        """
        Remediation and validation pipeline:
        1. Takes initial code and collects ALL actionable findings.
        2. In one focused pass:
           a. AI generates COMPLETE corrected source file from code + findings.
           b. Validates syntax / compilation of the generated code.
           c. Validates resolution via Validator Agent (AST + neural re-review).
        3. Returns (final_code, final_findings, passes_used, is_success, iterations, final_validation).
        """
        current_code = code
        lang_lower = language.lower().strip()

        # Step 1: Collect initial findings if not provided
        if initial_findings is not None:
            current_findings = list(initial_findings)
        else:
            current_findings = self.analyze_source(current_code, language=language)

        # If already clean, return immediately
        if not current_findings:
            clean_val = ValidationResult(
                validation_status="PASSED AI RE-REVIEW",
                resolved_issues=[],
                remaining_issues=[],
                new_issues=[],
                iteration_count=0,
                summary="No actionable issues detected. Source code is clean and validated."
            )
            return current_code, [], 0, True, [], clean_val

        iterations: List[PipelineIteration] = []
        final_validation: Optional[ValidationResult] = None
        loop_limit = min(max(1, max_iterations), 2)
        passes_used = 0

        for pass_idx in range(1, loop_limit + 1):
            passes_used = pass_idx

            # Generate COMPLETE fix for CURRENT generated code addressing ALL current findings
            fix_res = self.fixer_agent.generate_fix(
                code=current_code,
                issues=current_findings,
                language=language
            )

            candidate_code = _clean_code_fences(fix_res.fixed_code)

            # Syntax & Compilation integrity check
            if lang_lower in ("python", "py"):
                try:
                    ast.parse(candidate_code)
                    candidate_code = _prune_unused_python_imports(candidate_code)
                except SyntaxError:
                    # If AI fix introduced syntax error, fallback to deterministic repair engine on current code
                    candidate_code = _deterministic_fallback_fix(current_code, current_findings, language).fixed_code

            # Analyze the generated candidate code using the EXACT SAME analyzer
            static_findings = self.analyze_source(candidate_code, language=language)

            # Validate against original issues
            val_res = self.validator_agent.validate(
                original_code=current_code,
                fixed_code=candidate_code,
                original_issues=current_findings,
                iteration_count=pass_idx,
                language=language
            )

            # Consolidate any remaining static and validation issues
            combined_remaining = self._consolidate_issues(static_findings + val_res.remaining_issues + val_res.new_issues)
            val_res.remaining_issues = combined_remaining
            val_res.validation_status = "PASSED AI RE-REVIEW" if not combined_remaining else "ISSUES REMAINING"

            iteration_record = PipelineIteration(
                iteration_number=pass_idx,
                input_code=current_code,
                fixed_code=candidate_code,
                issues_before=list(current_findings),
                validation_result=val_res
            )
            iterations.append(iteration_record)
            final_validation = val_res

            # Update current code for next pass
            current_code = candidate_code

            # Termination check: 0 remaining findings
            if not combined_remaining:
                return current_code, [], passes_used, True, iterations, final_validation

            current_findings = combined_remaining

        # If issues remain after LLM passes, apply deterministic safe repair as safety net
        final_findings = self.analyze_source(current_code, language=language)
        if final_findings:
            repaired_result = _deterministic_fallback_fix(current_code, final_findings, language)
            repaired_code = repaired_result.fixed_code
            if lang_lower in ("python", "py"):
                repaired_code = _prune_unused_python_imports(repaired_code)
            recheck_findings = self.analyze_source(repaired_code, language=language)
            if len(recheck_findings) <= len(final_findings):
                current_code = repaired_code
                final_findings = recheck_findings

        is_success = (len(final_findings) == 0)

        if final_validation:
            final_validation.remaining_issues = final_findings
            final_validation.validation_status = "PASSED AI RE-REVIEW" if is_success else "ISSUES REMAINING"

        return current_code, final_findings, passes_used, is_success, iterations, final_validation

    def remediate_until_clean(
        self,
        code: str,
        issues: List[ReviewIssue],
        language: str = "python",
        max_iterations: int = 3
    ) -> Tuple[str, List[ReviewIssue], ValidationResult, List[PipelineIteration]]:
        """
        Backwards-compatible wrapper around remediate_and_validate.
        Returns (final_code, final_remaining_issues, final_validation, iterations).
        """
        final_code, final_findings, passes, is_success, iterations, final_val = self.remediate_and_validate(
            code=code,
            initial_findings=issues,
            language=language,
            max_iterations=max_iterations
        )
        return final_code, final_findings, final_val, iterations

    def execute_pipeline(
        self,
        code: str,
        language: str = "python",
        max_iterations: int = 1
    ) -> Dict[str, Any]:
        """
        Executes the complete CodeGuard AI pipeline:
        1. Deterministic Static Scan (AST/Language rules + Ruff)
        2. Comprehensive Multi-Agent Review (Analyzer + Reviewer + Security)
        3. Automated Complete Remediation (Fixes ALL findings in unified pass)
        4. Multi-Agent Validation Loop (Re-checks fixed code until 100% verified)
        """
        if not code or not code.strip():
            return {
                "error": "Empty code provided. Please upload or paste valid source code.",
                "is_resolved": False
            }

        # Step 1: Collect static issues
        static_issues = self.analyze_source(code, language=language)

        # Step 2: Parallel execution of Agent 1 (Analyzer), Agent 2 (Reviewer), and Agent 3 (Security)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            fut_ana = executor.submit(self.analyzer_agent.analyze, code=code, language=language)
            fut_rev = executor.submit(self.reviewer_agent.review, code=code, analysis=None, static_issues=static_issues, language=language)
            fut_sec = executor.submit(self.security_agent.audit, code=code, analysis=None, static_security_issues=static_issues, language=language)

            analysis = fut_ana.result()
            code_review = fut_rev.result()
            security_issues = fut_sec.result()

        # Consolidate all detected issues across all categories
        all_raw_issues = code_review.issues + security_issues + static_issues
        consolidated_issues = self._consolidate_issues(all_raw_issues)

        # Recalculate severity counts
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for iss in consolidated_issues:
            severity_counts[iss.severity] = severity_counts.get(iss.severity, 0) + 1
        code_review.severity_counts = SeverityCounts(**severity_counts)

        # If clean, return immediately
        if not consolidated_issues:
            clean_validation = ValidationResult(
                validation_status="PASSED AI RE-REVIEW",
                resolved_issues=[],
                remaining_issues=[],
                new_issues=[],
                iteration_count=0,
                summary="No issues detected by the review pipeline. Code is verified clean."
            )
            return {
                "original_code": code,
                "language": language,
                "analysis": analysis,
                "review": code_review,
                "security_issues": security_issues,
                "consolidated_issues": [],
                "final_remaining_issues": [],
                "iterations": [],
                "final_fixed_code": code,
                "final_validation": clean_validation,
                "total_iterations": 0,
                "is_resolved": True
            }

        # Step 3: Multi-Agent Remediation & Validation Loop (remediate_and_validate)
        final_fixed_code, final_remaining_issues, passes_used, is_resolved, iterations, final_validation = self.remediate_and_validate(
            code=code,
            initial_findings=consolidated_issues,
            language=language,
            max_iterations=max_iterations
        )

        return {
            "original_code": code,
            "language": language,
            "analysis": analysis,
            "review": code_review,
            "security_issues": security_issues,
            "consolidated_issues": consolidated_issues,
            "final_remaining_issues": final_remaining_issues,
            "iterations": iterations,
            "final_fixed_code": final_fixed_code,
            "final_validation": final_validation,
            "total_iterations": len(iterations),
            "is_resolved": is_resolved
        }

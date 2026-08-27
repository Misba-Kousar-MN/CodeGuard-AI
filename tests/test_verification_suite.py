import os
import unittest
from core.orchestrator import CodeGuardOrchestrator
from core.llm import GeminiLLMProvider
from core.schemas import (
    AnalysisResult,
    ReviewResult,
    ReviewIssue,
    FixResult,
    ValidationResult
)
from analyzers.static_analysis import run_static_analysis

class TestPhase3VerificationSuite(unittest.TestCase):

    def setUp(self):
        sample_dir = os.path.join(os.path.dirname(__file__), "sample_codes")
        with open(os.path.join(sample_dir, "test_case_a.py"), "r", encoding="utf-8") as f:
            self.code_a = f.read()
        with open(os.path.join(sample_dir, "test_case_b.py"), "r", encoding="utf-8") as f:
            self.code_b = f.read()

    def test_case_a_static_analysis(self):
        """Test Case A: Intentionally Bad Code Detection"""
        issues = run_static_analysis(self.code_a)
        titles = [i.title for i in issues]
        categories = [i.category for i in issues]

        # Verify exact static detections
        self.assertTrue(any("Hardcoded" in t or "Secret" in t for t in titles), "Must detect hardcoded API key")
        self.assertTrue(any("eval()" in t for t in titles), "Must detect dangerous eval()")
        self.assertTrue(any("shell=True" in t for t in titles), "Must detect shell=True")
        self.assertTrue(any("Bare `except:`" in t for t in titles), "Must detect bare except")
        self.assertTrue(any("Division" in t for t in titles), "Must detect division by zero risk")

    def test_case_b_clean_code(self):
        """Test Case B: Clean Code No Invented Bugs"""
        issues = run_static_analysis(self.code_b)
        self.assertEqual(len(issues), 0, "Clean code must not invent deterministic bugs")

    def test_structured_output_types(self):
        """Verify that Pydantic models instantiate strictly without type errors"""
        analysis = AnalysisResult(
            language="python",
            purpose="Test Purpose",
            components=["func1"],
            risk_areas=["none"],
            summary="Clean"
        )
        self.assertIsInstance(analysis, AnalysisResult)

        issue = ReviewIssue(
            category="Logic Bug",
            severity="HIGH",
            line=5,
            title="Division by Zero",
            description="Denominator unvalidated",
            impact="Crash",
            recommendation="Add check",
            evidence="x / y",
            source="Deterministic (AST)"
        )
        self.assertIsInstance(issue, ReviewIssue)

        rev_result = ReviewResult(
            summary="Review Complete",
            issues=[issue],
            severity_counts={"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0},
            overall_assessment="Action required"
        )
        self.assertIsInstance(rev_result, ReviewResult)

        fix_result = FixResult(
            fixed_code="def safe(): pass",
            changes_made=["Added pass"],
            explanation="Fixed"
        )
        self.assertIsInstance(fix_result, FixResult)

        val_result = ValidationResult(
            validation_status="PASSED AI RE-REVIEW",
            resolved_issues=["Division by Zero"],
            remaining_issues=[],
            new_issues=[],
            iteration_count=1,
            summary="Validation Passed"
        )
        self.assertIsInstance(val_result, ValidationResult)

    def test_fallback_mode_without_key(self):
        """Test application behavior when GEMINI_API_KEY is empty/absent"""
        provider = GeminiLLMProvider(api_key="")
        self.assertFalse(provider.is_available(), "Provider must be unavailable with empty key")

        orchestrator = CodeGuardOrchestrator(llm_provider=provider)
        res = orchestrator.execute_pipeline(self.code_a, max_iterations=3)

        self.assertIn("original_code", res)
        self.assertIn("consolidated_issues", res)
        # AST detections still present in fallback mode
        self.assertGreater(len(res["consolidated_issues"]), 0, "AST static findings must still work in fallback mode")
        self.assertIsNotNone(res["final_validation"])

if __name__ == "__main__":
    unittest.main()

import os
import unittest
from core.orchestrator import CodeGuardOrchestrator
from core.llm import GeminiLLMProvider

class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        sample_dir = os.path.join(os.path.dirname(__file__), "sample_codes")
        with open(os.path.join(sample_dir, "buggy_code.py"), "r", encoding="utf-8") as f:
            self.buggy_code = f.read()
        with open(os.path.join(sample_dir, "clean_code.py"), "r", encoding="utf-8") as f:
            self.clean_code = f.read()

    def test_buggy_pipeline_execution(self):
        orchestrator = CodeGuardOrchestrator()
        res = orchestrator.execute_pipeline(self.buggy_code, max_iterations=3)

        self.assertNotIn("error", res)
        self.assertIsNotNone(res["analysis"])
        self.assertIsNotNone(res["review"])
        self.assertIsNotNone(res["final_validation"])

        # Check issues detected
        issues = res["consolidated_issues"]
        self.assertGreater(len(issues), 0, "Pipeline must find issues in buggy sample code")

        # Check self-review iterations
        self.assertGreater(res["total_iterations"], 0, "At least 1 fix-validation iteration should occur")
        first_iteration = res["iterations"][0]
        self.assertIsNotNone(first_iteration.fixed_code)
        self.assertIsNotNone(first_iteration.validation_result)

    def test_clean_pipeline_execution(self):
        orchestrator = CodeGuardOrchestrator()
        res = orchestrator.execute_pipeline(self.clean_code, max_iterations=3)

        self.assertNotIn("error", res)
        self.assertEqual(len(res["consolidated_issues"]), 0, "Clean code should have 0 consolidated issues")
        self.assertTrue(res["is_resolved"], "Clean code should immediately pass review")
        self.assertEqual(res["total_iterations"], 0)

if __name__ == "__main__":
    unittest.main()

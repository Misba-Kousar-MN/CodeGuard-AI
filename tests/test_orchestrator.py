import os
import unittest
from core.orchestrator import CodeGuardOrchestrator
from core.llm import GeminiLLMProvider

class TestOrchestrator(unittest.TestCase):

    def setUp(self):
        sample_dir = os.path.join(os.path.dirname(__file__), "sample_codes")
        with open(os.path.join(sample_dir, "buggy_code.py"), "r", encoding="utf-8") as f:
            self.buggy_code = f.read()

    def test_orchestrator_pipeline_structure(self):
        # Create orchestrator (runs in offline mode if GEMINI_API_KEY is not set)
        orchestrator = CodeGuardOrchestrator()
        result = orchestrator.execute_pipeline(self.buggy_code, max_iterations=2)

        self.assertIn("original_code", result)
        self.assertIn("analysis", result)
        self.assertIn("review", result)
        self.assertIn("consolidated_issues", result)
        self.assertIn("final_validation", result)

        # Ensure AST detected issues are present in consolidated_issues
        self.assertGreater(len(result["consolidated_issues"]), 0, "Pipeline must consolidate detected issues")

if __name__ == "__main__":
    unittest.main()

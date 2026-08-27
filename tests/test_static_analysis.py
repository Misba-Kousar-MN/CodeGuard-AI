import os
import unittest
from analyzers.static_analysis import run_static_analysis

class TestStaticAnalysis(unittest.TestCase):

    def setUp(self):
        sample_dir = os.path.join(os.path.dirname(__file__), "sample_codes")
        with open(os.path.join(sample_dir, "buggy_code.py"), "r", encoding="utf-8") as f:
            self.buggy_code = f.read()
        with open(os.path.join(sample_dir, "clean_code.py"), "r", encoding="utf-8") as f:
            self.clean_code = f.read()

    def test_buggy_code_detection(self):
        issues = run_static_analysis(self.buggy_code)
        categories = [i.category for i in issues]
        titles = [i.title for i in issues]

        # 1. Hardcoded API key
        self.assertTrue(any("Hardcoded" in t for t in titles), "Should detect hardcoded API key")
        
        # 2. eval() usage
        self.assertTrue(any("eval()" in t for t in titles), "Should detect dangerous eval()")
        
        # 3. subprocess shell=True
        self.assertTrue(any("shell=True" in t for t in titles), "Should detect shell=True")
        
        # 4. Bare except
        self.assertTrue(any("Bare `except:`" in t for t in titles), "Should detect bare except")
        
        # 5. Division by zero literal
        self.assertTrue(any("Division" in t for t in titles), "Should detect division by zero")

    def test_clean_code_detection(self):
        issues = run_static_analysis(self.clean_code)
        self.assertEqual(len(issues), 0, "Clean code should trigger 0 AST issues")

    def test_empty_code_detection(self):
        issues = run_static_analysis("")
        self.assertEqual(len(issues), 0, "Empty code should trigger 0 AST issues")

if __name__ == "__main__":
    unittest.main()

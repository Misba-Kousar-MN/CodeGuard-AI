import unittest
import re
import ast
from core.orchestrator import CodeGuardOrchestrator
from analyzers.static_analysis import run_static_analysis

class TestApplyFixCompleteRemediation(unittest.TestCase):
    def test_one_click_multi_flaw_complete_remediation(self):
        """
        Verify that multi-flaw code with multiple functions:
        - calculate_discount()
        - execute_user_command()
        - read_data_file()
        is 100% remediated in a single Apply Fix run,
        retaining ALL functions and resolving ALL flaws with 0 remaining actionable issues.
        """
        sample_code = '''import os
import subprocess

API_KEY = "AIzaSyD9x8K11223344556677889900aabbcc"

def calculate_discount(price, count):
    average = price / count
    if price > 100 and price < 50:
        discount = 0.2
    else:
        discount = 0.05
    return average * (1 - discount)

def execute_user_command(user_input):
    res = eval(user_input)
    subprocess.run(f"echo {user_input}", shell=True)
    return res

def read_data_file(filename):
    try:
        with open(filename, "r") as f:
            return f.read()
    except:
        print("Error reading file")
        return None
'''
        orchestrator = CodeGuardOrchestrator()
        
        # Step 1: Detect actionable issues (Review)
        initial_static = run_static_analysis(sample_code, language="python")
        self.assertGreater(len(initial_static), 0, "Should detect multiple flaws in original code")
        
        # Step 2: One-click remediation loop
        final_code, final_remaining, final_validation, iterations = orchestrator.remediate_until_clean(
            code=sample_code,
            issues=initial_static,
            language="python",
            max_iterations=3
        )
        
        # Verify complete file integrity: all functions must be present
        tree = ast.parse(final_code)
        func_names = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertIn("calculate_discount", func_names, "calculate_discount must be preserved")
        self.assertIn("execute_user_command", func_names, "execute_user_command must be preserved")
        self.assertIn("read_data_file", func_names, "read_data_file must be preserved")
        
        # Verify all vulnerabilities resolved
        self.assertNotIn("AIzaSy", final_code, "API key should be loaded via os.getenv")
        self.assertIsNone(re.search(r'\beval\(', final_code), "Dangerous eval() should be replaced with ast.literal_eval()")
        self.assertNotIn("shell=True", final_code, "shell=True should be removed")
        self.assertNotIn("except:", final_code, "Bare except should be replaced with Exception")
        
        # Verify static re-analysis on final code passes with 0 issues
        re_analysis = run_static_analysis(final_code, language="python")
        self.assertEqual(len(re_analysis), 0, f"Remaining issues found in fixed code: {re_analysis}")
        self.assertEqual(len(final_remaining), 0, "No actionable issues should remain")

if __name__ == "__main__":
    unittest.main()

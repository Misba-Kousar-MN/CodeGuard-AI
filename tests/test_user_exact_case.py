import sys
import unittest
import ast

from core.orchestrator import CodeGuardOrchestrator

class TestUserExactCase(unittest.TestCase):
    def setUp(self):
        self.orchestrator = CodeGuardOrchestrator()

    def test_exact_user_code_complete_remediation_and_fresh_review(self):
        """
        Tests user's exact code:
        Review Code -> Apply Fix ONCE -> Copy AFTER code -> New Review -> 0 issues detected!
        """
        user_code = """import os
import subprocess

DATABASE_PASSWORD = "admin123"

def calculate_total(price, quantity):
    average_price = price / quantity

    if price > 100 and price < 50:
        discount = 0.20
    else:
        discount = 0.05

    return average_price * (1 - discount)

def execute_command(user_input):
    result = eval(user_input)
    subprocess.run(user_input, shell=True)
    return result

def find_user(users, username):
    for i in range(len(users)):
        if users[i]["name"] == username:
            return users[i]
    return None
"""

        # Step 1: Initial review on original code
        initial_res = self.orchestrator.execute_pipeline(user_code, language="python", max_iterations=3)
        initial_issues = initial_res.get("consolidated_issues", [])
        self.assertGreater(len(initial_issues), 0, "Original code must have detected issues")

        # Step 2: Apply Fix (remediate_and_validate)
        final_code, final_findings, passes, is_success, iterations, val = self.orchestrator.remediate_and_validate(
            code=user_code,
            initial_findings=initial_issues,
            language="python",
            max_iterations=3
        )

        print("\n==========================================")
        print("GENERATED AFTER / FIXED CODE:")
        print("==========================================")
        print(final_code)
        print("==========================================")
        print(f"Passes used: {passes}, is_success: {is_success}, remaining findings: {len(final_findings)}")

        # Step 3: Verify all 3 original functions are preserved in fixed code
        tree = ast.parse(final_code)
        funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertIn("calculate_total", funcs)
        self.assertIn("execute_command", funcs)
        self.assertIn("find_user", funcs)

        # Step 4: Verify 0 remaining findings
        self.assertEqual(len(final_findings), 0, "Remediation loop must leave 0 remaining findings")
        self.assertTrue(is_success, "Remediation must succeed")

        # Step 5: CRITICAL TEST - Fresh new Review on the generated AFTER code
        fresh_review_res = self.orchestrator.execute_pipeline(final_code, language="python", max_iterations=3)
        fresh_issues = fresh_review_res.get("consolidated_issues", [])
        print(f"\nFresh new review on AFTER code found {len(fresh_issues)} issues:")
        for iss in fresh_issues:
            print(f"  - [{iss.category}] Line {iss.line}: {iss.title} - {iss.description}")

        self.assertEqual(len(fresh_issues), 0, "A completely new review on the fixed code must detect ZERO issues!")

if __name__ == "__main__":
    unittest.main()

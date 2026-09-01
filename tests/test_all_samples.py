import sys
import unittest
import ast
import re

from core.orchestrator import CodeGuardOrchestrator
from analyzers.static_analysis import run_static_analysis

class TestAllSamplesRemediation(unittest.TestCase):
    def setUp(self):
        self.orchestrator = CodeGuardOrchestrator()

    def test_python_buggy_preset(self):
        code = """import subprocess

API_KEY = "AIzaSyD9x8K11223344556677889900aabbcc"

def calculate_discount(price, count):
    # Potential division by zero if count is 0
    average = price / count
    
    # Incorrect logical condition
    if price > 100 and price < 50:
        discount = 0.2
    else:
        discount = 0.05
    return average * (1 - discount)

def execute_user_command(user_input):
    # Security Flaws: Dangerous eval and shell=True
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
"""
        initial_issues = run_static_analysis(code, language="python")
        final_code, final_remaining, val_res, iters = self.orchestrator.remediate_until_clean(
            code=code,
            issues=initial_issues,
            language="python",
            max_iterations=3
        )
        print("PYTHON BUGGY FIXED CODE:\n", final_code)
        print("PYTHON BUGGY REMAINING:", final_remaining)
        tree = ast.parse(final_code)
        funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertIn("calculate_discount", funcs)
        self.assertIn("execute_user_command", funcs)
        self.assertIn("read_data_file", funcs)
        self.assertEqual(len(final_remaining), 0)

    def test_python_logic_preset(self):
        code = """def compute_ratio(a, b):
    # Missing zero check
    return a / b

def check_range(val):
    # Impossible condition
    if val > 100 and val < 10:
        return True
    return False
"""
        initial_issues = run_static_analysis(code, language="python")
        final_code, final_remaining, val_res, iters = self.orchestrator.remediate_until_clean(
            code=code,
            issues=initial_issues,
            language="python",
            max_iterations=3
        )
        print("PYTHON LOGIC FIXED CODE:\n", final_code)
        print("PYTHON LOGIC REMAINING:", final_remaining)
        tree = ast.parse(final_code)
        funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertIn("compute_ratio", funcs)
        self.assertIn("check_range", funcs)
        self.assertEqual(len(final_remaining), 0)

    def test_cpp_buggy_preset(self):
        code = """#include <iostream>
#include <cstring>
#include <cstdlib>

const char* API_KEY = "AIzaSyB3344556677889900112233445566";

void process_input(const char* user_input) {
    char buffer[16];
    // Dangerous buffer overflow vulnerability
    strcpy(buffer, user_input);
    
    // Command injection vulnerability
    char cmd[128];
    sprintf(cmd, "echo %s", buffer);
    system(cmd);
}

double calculate_ratio(double total, int count) {
    // Missing zero division check
    return total / count;
}

int main() {
    process_input("hello");
    std::cout << calculate_ratio(100.0, 0) << std::endl;
    return 0;
}
"""
        initial_issues = run_static_analysis(code, language="cpp")
        final_code, final_remaining, val_res, iters = self.orchestrator.remediate_until_clean(
            code=code,
            issues=initial_issues,
            language="cpp",
            max_iterations=3
        )
        print("CPP BUGGY FIXED CODE:\n", final_code)
        print("CPP BUGGY REMAINING:", final_remaining)
        self.assertIn("void process_input", final_code)
        self.assertIn("calculate_ratio", final_code)
        self.assertIn("int main", final_code)
        self.assertEqual(len(final_remaining), 0)

    def test_cpp_logic_preset(self):
        code = """#include <iostream>
#include <vector>

int get_element(const std::vector<int>& arr, int index) {
    // Off-by-one boundary error: using <= instead of <
    if (index <= arr.size()) {
        return arr[index];
    }
    return -1;
}

double divide_values(double a, double b) {
    // Missing zero divisor validation
    return a / b;
}
"""
        initial_issues = run_static_analysis(code, language="cpp")
        final_code, final_remaining, val_res, iters = self.orchestrator.remediate_until_clean(
            code=code,
            issues=initial_issues,
            language="cpp",
            max_iterations=3
        )
        print("CPP LOGIC FIXED CODE:\n", final_code)
        print("CPP LOGIC REMAINING:", final_remaining)
        self.assertIn("get_element", final_code)
        self.assertIn("divide_values", final_code)
        self.assertEqual(len(final_remaining), 0)

    def test_java_buggy_preset(self):
        code = """import java.io.*;

public class PaymentService {
    private static final String API_KEY = "AIzaSyC99887766554433221100aabbccdd";

    public static void runCommand(String userInput) {
        try {
            // Dangerous command injection
            Runtime.getRuntime().exec("sh -c " + userInput);
        } catch (Exception e) {
            // Overly broad empty catch
        }
    }

    public static double computeDiscount(double total, int count) {
        // Missing zero division check
        double avg = total / count;
        return avg;
    }

    public static String readFile(String path) {
        try {
            // Potential resource leak without try-with-resources
            FileInputStream fis = new FileInputStream(path);
            return new String(fis.readAllBytes());
        } catch (Exception e) {
            return null;
        }
    }
}
"""
        initial_issues = run_static_analysis(code, language="java")
        final_code, final_remaining, val_res, iters = self.orchestrator.remediate_until_clean(
            code=code,
            issues=initial_issues,
            language="java",
            max_iterations=3
        )
        print("JAVA BUGGY FIXED CODE:\n", final_code)
        print("JAVA BUGGY REMAINING:", final_remaining)
        self.assertIn("PaymentService", final_code)
        self.assertIn("runCommand", final_code)
        self.assertIn("computeDiscount", final_code)
        self.assertIn("readFile", final_code)
        self.assertEqual(len(final_remaining), 0)

    def test_java_logic_preset(self):
        code = """public class MathUtils {
    public static double divide(double a, double b) {
        // Missing zero validation
        return a / b;
    }

    public static boolean checkRange(int val) {
        // Impossible logical condition
        if (val > 100 && val < 10) {
            return true;
        }
        return false;
    }
}
"""
        initial_issues = run_static_analysis(code, language="java")
        final_code, final_remaining, val_res, iters = self.orchestrator.remediate_until_clean(
            code=code,
            issues=initial_issues,
            language="java",
            max_iterations=3
        )
        print("JAVA LOGIC FIXED CODE:\n", final_code)
        print("JAVA LOGIC REMAINING:", final_remaining)
        self.assertIn("MathUtils", final_code)
        self.assertIn("divide", final_code)
        self.assertIn("checkRange", final_code)
        self.assertEqual(len(final_remaining), 0)

    def test_sample_test_case_a(self):
        with open("tests/sample_codes/test_case_a.py", "r") as f:
            code = f.read()
        initial_issues = run_static_analysis(code, language="python")
        final_code, final_remaining, val_res, iters = self.orchestrator.remediate_until_clean(
            code=code,
            issues=initial_issues,
            language="python",
            max_iterations=3
        )
        print("TEST CASE A FIXED CODE:\n", final_code)
        print("TEST CASE A REMAINING:", final_remaining)
        tree = ast.parse(final_code)
        funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertIn("run_command", funcs)
        self.assertIn("calculate_average", funcs)
        self.assertIn("execute", funcs)
        self.assertEqual(len(final_remaining), 0)

if __name__ == "__main__":
    unittest.main()

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

    def test_cpp_static_analysis(self):
        cpp_code = """
        #include <iostream>
        #include <cstring>
        const char* API_KEY = "AIzaSyD9x8K11223344556677889900aabbcc";
        void test(char* in) {
            char buf[10];
            strcpy(buf, in);
            system("echo test");
            int x = 10 / 0;
        }
        """
        issues = run_static_analysis(cpp_code, language="cpp")
        titles = [i.title for i in issues]
        self.assertTrue(any("Hardcoded" in t for t in titles), "Should detect C++ hardcoded secret")
        self.assertTrue(any("strcpy" in t for t in titles), "Should detect C++ strcpy overflow")
        self.assertTrue(any("system" in t for t in titles), "Should detect C++ system command")
        self.assertTrue(any("Division" in t for t in titles), "Should detect C++ division by zero")

    def test_java_static_analysis(self):
        java_code = """
        public class Test {
            private String API_KEY = "AIzaSyD9x8K11223344556677889900aabbcc";
            public void run(String cmd) {
                try {
                    Runtime.getRuntime().exec(cmd);
                    int val = 100 / 0;
                } catch (Exception e) {}
            }
        }
        """
        issues = run_static_analysis(java_code, language="java")
        titles = [i.title for i in issues]
        self.assertTrue(any("Hardcoded" in t for t in titles), "Should detect Java hardcoded secret")
        self.assertTrue(any("Runtime.exec" in t for t in titles), "Should detect Java Runtime.exec")
        self.assertTrue(any("Division" in t for t in titles), "Should detect Java division by zero")
        self.assertTrue(any("catch" in t.lower() for t in titles), "Should detect Java broad catch")

if __name__ == "__main__":
    unittest.main()

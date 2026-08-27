import os
import subprocess

# Test Sample containing multiple bugs and security flaws
API_KEY = "AIzaSyD9x8K11223344556677889900aabbcc"  # Hardcoded secret

def calculate_discount(price, count):
    # Bug 1: Division by zero risk if count is 0
    average = price / count
    
    # Bug 2: Incorrect logical condition (should be price >= 100)
    if price > 100 and price < 50:
        discount = 0.2
    else:
        discount = 0.05
    return average * (1 - discount)

def execute_user_command(user_input):
    # Security Flaw 1: Dangerous eval
    res = eval(user_input)
    
    # Security Flaw 2: Unsafe subprocess with shell=True
    subprocess.run(f"echo {user_input}", shell=True)
    return res

def read_data_file(filename):
    try:
        with open(filename, "r") as f:
            return f.read()
    except:  # Quality Flaw: Bare except
        print("Error reading file")
        return None

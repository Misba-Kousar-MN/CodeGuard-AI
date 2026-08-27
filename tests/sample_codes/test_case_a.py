import subprocess

API_KEY = "AIzaSy1234567890abcdefghijklmnop"

def run_command(user_input):
    result = subprocess.run(user_input, shell=True)
    return result.stdout

def calculate_average(numbers):
    return sum(numbers) / len(numbers)

def execute(code):
    return eval(code)

try:
    print("Hello")
except:
    pass

# Simple test for CodeRabbit
# This file has obvious issues that should trigger CodeRabbit

def bad_function():
    # Missing docstring
    x = 1
    y = 2
    return x + y

# Security issue - hardcoded password
PASSWORD = "secret123"

# Bad variable names
a = 1
b = 2

# Unused import
import os

# Long line that exceeds PEP 8
def very_long_function_name_that_exceeds_the_recommended_line_length_limit_and_should_trigger_a_warning():
    return "This line is too long"

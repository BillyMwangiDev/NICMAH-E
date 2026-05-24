# Test file for CodeRabbit review
# This file contains intentional issues to test CodeRabbit suggestions

import os
import sys
from django.db import models
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.models import User

# Missing docstring - should trigger documentation warning
def bad_function():
    # No docstring
    x = 1
    y = 2
    return x + y

# Security issue - SQL injection vulnerability
def vulnerable_query(request):
    user_input = request.GET.get('id')
    query = f"SELECT * FROM users WHERE id = {user_input}"  # SQL injection risk
    return HttpResponse("Query executed")

# Performance issue - N+1 query problem
def n_plus_one_problem():
    users = User.objects.all()
    for user in users:
        # This will cause N+1 queries
        print(user.profile.bio)  # Assuming profile exists

# Code quality issue - complex function
def very_complex_function(a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, r, s, t, u, v, w, x, y, z):
    # Too many parameters - should trigger complexity warning
    result = 0
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if f > 0:
                            if g > 0:
                                if h > 0:
                                    if i > 0:
                                        if j > 0:
                                            if k > 0:
                                                if l > 0:
                                                    if m > 0:
                                                        if n > 0:
                                                            if o > 0:
                                                                if p > 0:
                                                                    if q > 0:
                                                                        if r > 0:
                                                                            if s > 0:
                                                                                if t > 0:
                                                                                    if u > 0:
                                                                                        if v > 0:
                                                                                            if w > 0:
                                                                                                if x > 0:
                                                                                                    if y > 0:
                                                                                                        if z > 0:
                                                                                                            result = 1
    return result

# Hardcoded secrets - security issue
SECRET_KEY = "my-super-secret-key-12345"  # Should be in environment variables
DATABASE_PASSWORD = "password123"  # Should be in environment variables

# Unused imports
import json
import xml.etree.ElementTree  # Unused import

# Bad variable names
a = 1
b = 2
c = 3

# Duplicate code
def duplicate_function1():
    x = 1
    y = 2
    z = x + y
    return z

def duplicate_function2():
    x = 1
    y = 2
    z = x + y
    return z

# Missing error handling
def no_error_handling(request):
    user_id = request.GET.get('id')
    user = User.objects.get(id=user_id)  # No try-catch
    return HttpResponse(f"User: {user.username}")

# Inefficient code
def inefficient_code():
    numbers = []
    for i in range(1000):
        numbers.append(i)  # Should use list comprehension
    return numbers

# Bad Django practice - raw SQL without proper escaping
def raw_sql_vulnerable(request):
    from django.db import connection
    user_input = request.GET.get('search')
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM products WHERE name LIKE '%{user_input}%'")
        return cursor.fetchall()

# Missing CSRF protection (though this would be in a real view)
def no_csrf_protection(request):
    if request.method == 'POST':
        # No CSRF check
        return HttpResponse("Data saved")

# Hardcoded URLs
def hardcoded_urls():
    return [
        "http://localhost:8000/admin/",
        "http://localhost:8000/api/users/",
        "http://localhost:8000/static/css/main.css"
    ]

# Bad exception handling
def bad_exception_handling():
    try:
        result = 1 / 0
    except:  # Bare except clause
        pass

# Missing type hints
def no_type_hints(param1, param2):
    return param1 + param2

# Inconsistent naming
def camelCaseFunction():  # Should be snake_case
    pass

def snake_case_function():  # This is correct
    pass

# Magic numbers
def magic_numbers():
    if age > 18:  # Magic number
        return "Adult"
    elif age > 13:  # Magic number
        return "Teenager"
    else:
        return "Child"

# Long lines
def very_long_line_with_many_characters_that_exceeds_the_recommended_line_length_limit_and_should_trigger_a_warning_about_line_length():
    return "This line is too long and should trigger a warning"

# Missing logging
def no_logging():
    # No logging statements
    result = some_operation()
    return result

def some_operation():
    return "result"

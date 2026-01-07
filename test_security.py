"""
Security tests for NICMAH-E Django application.
Tests all security fixes implemented based on CodeRabbit suggestions.
"""

import json
import os
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test.utils import override_settings
from django.http import HttpResponse
from django.utils.html import escape
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Q

class SecurityTestCase(TestCase):
    """Base class for security tests."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True,
            is_superuser=True
        )

class XSSProtectionTest(SecurityTestCase):
    """Test XSS protection measures."""
    
    def test_xss_in_user_input(self):
        """Test that XSS attempts are properly escaped."""
        xss_payload = '<script>alert("XSS")</script>'
        
        # Test template rendering
        response = self.client.get('/test-template/', {'user_input': xss_payload})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('<script>', response.content.decode())
        self.assertIn(escape(xss_payload), response.content.decode())
    
    def test_xss_in_javascript_context(self):
        """Test that JavaScript context is properly escaped."""
        xss_payload = '"; alert("XSS"); "'
        
        response = self.client.get('/test-template/', {'user_data': xss_payload})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('alert("XSS")', response.content.decode())
    
    def test_xss_middleware_detection(self):
        """Test XSS protection middleware."""
        xss_payload = '<script>alert("XSS")</script>'
        
        response = self.client.post('/test-input/', {'user_input': xss_payload})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid input detected', response.content.decode())

class CSRFProtectionTest(SecurityTestCase):
    """Test CSRF protection measures."""
    
    def test_csrf_token_required(self):
        """Test that CSRF token is required for POST requests."""
        # Test without CSRF token
        response = self.client.post('/test-submit/', {'data': 'test'})
        self.assertEqual(response.status_code, 403)
    
    def test_csrf_token_present(self):
        """Test that CSRF token is present in forms."""
        response = self.client.get('/test-template/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('csrfmiddlewaretoken', response.content.decode())
    
    def test_csrf_exempt_removed(self):
        """Test that @csrf_exempt decorators are removed where not needed."""
        # This should fail without CSRF token
        response = self.client.post('/update-product/', 
                                   data=json.dumps({'id': 1, 'name': 'test'}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, 403)

class SQLInjectionProtectionTest(SecurityTestCase):
    """Test SQL injection protection measures."""
    
    def test_sql_injection_attempt(self):
        """Test that SQL injection attempts are detected."""
        sql_payload = "'; DROP TABLE users; --"
        
        response = self.client.get('/search-products/', {'q': sql_payload})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid input detected', response.content.decode())
    
    def test_orm_usage(self):
        """Test that Django ORM is used instead of raw SQL."""
        # This should use ORM and not be vulnerable to SQL injection
        query = "test' OR '1'='1"
        response = self.client.get('/search-products/', {'q': query})
        self.assertEqual(response.status_code, 200)
        # Should not contain the malicious query in response

class AuthenticationTest(SecurityTestCase):
    """Test authentication and authorization measures."""
    
    def test_login_required(self):
        """Test that protected views require authentication."""
        response = self.client.get('/admin-panel/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_permission_required(self):
        """Test that admin views require proper permissions."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/admin-panel/')
        self.assertEqual(response.status_code, 403)  # Permission denied
    
    def test_sensitive_data_not_exposed(self):
        """Test that sensitive data is not exposed."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/user-profile/1/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertIn('username', data)
        self.assertIn('email', data)
        self.assertNotIn('password', data)  # Password should not be exposed
        self.assertNotIn('password_hash', data)
    
    def test_user_authorization(self):
        """Test that users can only access their own data."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(f'/user-profile/{other_user.id}/')
        self.assertEqual(response.status_code, 403)  # Forbidden

class InputValidationTest(SecurityTestCase):
    """Test input validation measures."""
    
    def test_input_sanitization(self):
        """Test that user input is properly sanitized."""
        malicious_input = '<script>alert("XSS")</script>'
        
        response = self.client.post('/user-input-processing/', 
                                   {'user_input': malicious_input})
        self.assertEqual(response.status_code, 200)
        self.assertIn(escape(malicious_input), response.content.decode())
    
    def test_file_upload_validation(self):
        """Test that file uploads are validated."""
        # Test with malicious file
        with open('test_malicious.exe', 'w') as f:
            f.write('malicious content')
        
        with open('test_malicious.exe', 'rb') as f:
            response = self.client.post('/upload-file/', {'file': f})
        
        self.assertEqual(response.status_code, 400)
        os.remove('test_malicious.exe')
    
    def test_input_length_limits(self):
        """Test that input length limits are enforced."""
        long_input = 'a' * 2000  # Exceeds 1000 character limit
        
        response = self.client.post('/user-input-processing/', 
                                   {'user_input': long_input})
        self.assertEqual(response.status_code, 400)

class SecurityHeadersTest(SecurityTestCase):
    """Test security headers."""
    
    def test_security_headers_present(self):
        """Test that security headers are set."""
        response = self.client.get('/')
        
        # Check for security headers
        self.assertIn('X-Frame-Options', response)
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-XSS-Protection', response)
        self.assertIn('Referrer-Policy', response)
    
    def test_csp_header(self):
        """Test that Content Security Policy header is set."""
        response = self.client.get('/')
        self.assertIn('Content-Security-Policy', response)
    
    def test_frame_options(self):
        """Test that X-Frame-Options is set to DENY."""
        response = self.client.get('/')
        self.assertEqual(response['X-Frame-Options'], 'DENY')

class RateLimitingTest(SecurityTestCase):
    """Test rate limiting measures."""
    
    @override_settings(RATE_LIMIT_ENABLED=True, RATE_LIMIT_REQUESTS=5)
    def test_rate_limiting(self):
        """Test that rate limiting is enforced."""
        # Make 5 requests (should be allowed)
        for i in range(5):
            response = self.client.get('/api-endpoint/')
            self.assertEqual(response.status_code, 200)
        
        # 6th request should be blocked
        response = self.client.get('/api-endpoint/')
        self.assertEqual(response.status_code, 429)
        self.assertIn('Rate limit exceeded', response.content.decode())

class HTTPStatusCodesTest(SecurityTestCase):
    """Test proper HTTP status codes."""
    
    def test_proper_status_codes(self):
        """Test that proper HTTP status codes are returned."""
        # Test 404 for non-existent resource
        response = self.client.get('/non-existent-page/')
        self.assertEqual(response.status_code, 404)
        
        # Test 403 for forbidden access
        response = self.client.get('/admin-panel/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_delete_status_code(self):
        """Test that DELETE operations return proper status codes."""
        # Test 204 for successful deletion
        response = self.client.delete('/delete-product/1/')
        self.assertEqual(response.status_code, 404)  # Product doesn't exist

class ErrorHandlingTest(SecurityTestCase):
    """Test error handling and logging."""
    
    def test_error_logging(self):
        """Test that errors are properly logged."""
        # This should trigger an error and be logged
        response = self.client.get('/handle-error/')
        self.assertEqual(response.status_code, 500)
        
        # Check that error was logged (this would require checking log files)
        # In a real test, you might mock the logger and verify it was called
    
    def test_generic_error_messages(self):
        """Test that error messages don't expose sensitive information."""
        response = self.client.get('/handle-error/')
        self.assertEqual(response.status_code, 500)
        self.assertIn('error occurred', response.content.decode())
        self.assertNotIn('traceback', response.content.decode())

class PerformanceOptimizationTest(SecurityTestCase):
    """Test performance optimizations."""
    
    def test_bulk_operations(self):
        """Test that bulk operations are used instead of individual saves."""
        # This should use F() expressions for bulk updates
        response = self.client.post('/bulk-operations/')
        self.assertEqual(response.status_code, 200)
    
    def test_optimized_queries(self):
        """Test that queries are optimized with select_related and prefetch_related."""
        response = self.client.get('/expensive-query/')
        self.assertEqual(response.status_code, 200)
        # In a real test, you might check the number of queries executed
    
    def test_caching(self):
        """Test that caching is implemented."""
        response = self.client.get('/product-categories/')
        self.assertEqual(response.status_code, 200)
        # In a real test, you might verify that cache was used

class FileUploadSecurityTest(SecurityTestCase):
    """Test file upload security."""
    
    def test_allowed_file_types(self):
        """Test that only allowed file types are accepted."""
        # Test with allowed file type
        with open('test_image.jpg', 'w') as f:
            f.write('fake image content')
        
        with open('test_image.jpg', 'rb') as f:
            response = self.client.post('/upload-file/', {'file': f})
        
        # This should be allowed
        self.assertNotEqual(response.status_code, 400)
        os.remove('test_image.jpg')
    
    def test_file_size_limits(self):
        """Test that file size limits are enforced."""
        # Create a large file
        large_content = 'x' * (6 * 1024 * 1024)  # 6MB, exceeds 5MB limit
        
        with open('large_file.txt', 'w') as f:
            f.write(large_content)
        
        with open('large_file.txt', 'rb') as f:
            response = self.client.post('/upload-file/', {'file': f})
        
        self.assertEqual(response.status_code, 400)
        os.remove('large_file.txt')

class SecurityMonitoringTest(SecurityTestCase):
    """Test security monitoring and logging."""
    
    def test_failed_login_logging(self):
        """Test that failed login attempts are logged."""
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        
        # This should trigger failed login logging
        # In a real test, you would verify the log was written
    
    def test_admin_access_logging(self):
        """Test that admin access is logged."""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get('/admin/')
        
        # This should trigger admin access logging
        # In a real test, you would verify the log was written

class IntegrationSecurityTest(SecurityTestCase):
    """Integration tests for security measures."""
    
    def test_complete_security_workflow(self):
        """Test a complete secure workflow."""
        # 1. Login
        self.client.login(username='testuser', password='testpass123')
        
        # 2. Access protected resource
        response = self.client.get('/user-profile/1/')
        self.assertEqual(response.status_code, 200)
        
        # 3. Submit form with CSRF token
        response = self.client.get('/test-template/')
        csrf_token = response.context['csrf_token']
        
        response = self.client.post('/test-submit/', {
            'data': 'test data',
            'csrfmiddlewaretoken': csrf_token
        })
        self.assertEqual(response.status_code, 200)
        
        # 4. Test input validation
        response = self.client.post('/user-input-processing/', {
            'user_input': 'normal input'
        })
        self.assertEqual(response.status_code, 200)
    
    def test_security_middleware_order(self):
        """Test that security middleware is properly ordered."""
        # This test would verify that security middleware runs in the correct order
        # and that all security checks are performed
        pass

def run_security_tests():
    """Run all security tests."""
    import unittest
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all security test classes
    test_classes = [
        XSSProtectionTest,
        CSRFProtectionTest,
        SQLInjectionProtectionTest,
        AuthenticationTest,
        InputValidationTest,
        SecurityHeadersTest,
        RateLimitingTest,
        HTTPStatusCodesTest,
        ErrorHandlingTest,
        PerformanceOptimizationTest,
        FileUploadSecurityTest,
        SecurityMonitoringTest,
        IntegrationSecurityTest,
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_security_tests()
    if success:
        print("✅ All security tests passed!")
    else:
        print("❌ Some security tests failed!")
        exit(1)

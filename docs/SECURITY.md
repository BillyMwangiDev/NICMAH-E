# Security Documentation for NICMAH-E

## Overview

This document outlines the security measures implemented in the NICMAH-E Django application to address vulnerabilities identified by CodeRabbit and maintain a secure application environment.

## Security Issues Addressed

### 1. XSS (Cross-Site Scripting) Protection

**Issues Fixed:**
- Removed `|safe` filter from untrusted user input
- Added `|escapejs` filter for JavaScript context
- Implemented input sanitization middleware
- Added XSS pattern detection

**Implementation:**
```python
# Before (Vulnerable)
<div id="user-input">{{ user_input|safe }}</div>

# After (Secure)
<div id="user-input">{{ user_input }}</div>
```

**Best Practices:**
- Always escape user input in templates
- Use `|escapejs` for JavaScript context
- Validate and sanitize all user inputs
- Implement Content Security Policy (CSP)

### 2. CSRF (Cross-Site Request Forgery) Protection

**Issues Fixed:**
- Added `{% csrf_token %}` to all forms
- Removed `@csrf_exempt` decorators where not needed
- Implemented secure CSRF cookie settings

**Implementation:**
```html
<!-- Before (Vulnerable) -->
<form method="post" action="/submit">
    <input type="text" name="data">
    <button type="submit">Submit</button>
</form>

<!-- After (Secure) -->
<form method="post" action="/submit">
    {% csrf_token %}
    <input type="text" name="data">
    <button type="submit">Submit</button>
</form>
```

### 3. SQL Injection Protection

**Issues Fixed:**
- Replaced raw SQL queries with Django ORM
- Added SQL injection pattern detection
- Implemented parameterized queries

**Implementation:**
```python
# Before (Vulnerable)
products = Product.objects.raw(f"SELECT * FROM catalog_product WHERE name LIKE '%{query}%'")

# After (Secure)
products = Product.objects.filter(
    Q(name__icontains=query) | 
    Q(description__icontains=query)
)
```

### 4. Authentication and Authorization

**Issues Fixed:**
- Added `@login_required` decorators
- Implemented `@permission_required` checks
- Added proper user authorization checks
- Removed sensitive data exposure

**Implementation:**
```python
# Before (Vulnerable)
def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    return JsonResponse({
        'username': user.username,
        'email': user.email,
        'password_hash': user.password,  # Exposed sensitive data
        'is_active': user.is_active
    })

# After (Secure)
def user_profile(request, user_id):
    if not request.user.is_authenticated or request.user.id != int(user_id):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    user = get_object_or_404(User, id=user_id)
    return JsonResponse({
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
    })
```

### 5. Input Validation and Sanitization

**Issues Fixed:**
- Added input validation for all user inputs
- Implemented proper error handling
- Added file upload validation
- Sanitized user input to prevent XSS

**Implementation:**
```python
# Before (Vulnerable)
def user_input_processing(request):
    user_input = request.POST.get('user_input')
    return HttpResponse(f"Processed: {user_input}")

# After (Secure)
def user_input_processing(request):
    user_input = request.POST.get('user_input', '')
    if not user_input:
        return HttpResponse("No input provided", status=400)
    
    sanitized_input = escape(user_input)
    return HttpResponse(f"Processed: {sanitized_input}")
```

### 6. HTTP Security Headers

**Issues Fixed:**
- Added Content Security Policy (CSP)
- Implemented secure cookie settings
- Added security headers middleware
- Enforced HTTPS in production

**Implementation:**
```python
# Security Headers
SECURITY_HEADERS = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}
```

### 7. Rate Limiting

**Issues Fixed:**
- Implemented rate limiting middleware
- Added request throttling
- Protected against brute force attacks

**Implementation:**
```python
# Rate Limiting Configuration
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_BLOCK_DURATION = 60  # seconds
```

### 8. File Upload Security

**Issues Fixed:**
- Added file type validation
- Implemented file size limits
- Added virus scanning capability
- Stored files outside webroot

**Implementation:**
```python
# File Upload Security
FILE_UPLOAD_SECURITY = {
    'MAX_FILE_SIZE': 5 * 1024 * 1024,  # 5MB
    'ALLOWED_EXTENSIONS': ['.jpg', '.jpeg', '.png', '.gif', '.pdf'],
    'SCAN_FOR_VIRUSES': True,
    'STORE_OUTSIDE_WEBROOT': True,
}
```

## Security Middleware

The application includes several security middleware classes:

1. **SecurityHeadersMiddleware**: Adds security headers to all responses
2. **RateLimitMiddleware**: Implements rate limiting
3. **InputValidationMiddleware**: Validates and sanitizes user input
4. **CSRFProtectionMiddleware**: Enhanced CSRF protection
5. **SQLInjectionProtectionMiddleware**: Detects SQL injection attempts
6. **XSSProtectionMiddleware**: Detects XSS attempts
7. **SecurityMonitoringMiddleware**: Monitors and logs security events

## Security Configuration

### Environment Variables

Set these environment variables for production:

```bash
# HTTPS Settings
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Cookie Security
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Security Settings

The main security settings are defined in `nichmah_agrovet/security_settings.py`:

```python
# Import security settings in your main settings.py
from .security_settings import *

# Add security middleware
MIDDLEWARE += SECURITY_MIDDLEWARE
```

## Security Monitoring

### Logging

Security events are logged to `logs/security.log`:

```python
# Log security events
log_security_event(
    'FAILED_LOGIN',
    f'Failed login attempt from {ip_address}',
    ip_address=ip_address
)
```

### Monitoring Events

The following security events are monitored:

- Failed login attempts
- Admin access
- SQL injection attempts
- XSS attempts
- Rate limit exceeded
- Invalid file uploads
- CSRF failures

## Security Testing

### Automated Security Tests

Run security tests:

```bash
# Run security audit
python manage.py security_audit

# Run vulnerability scan
python manage.py vulnerability_scan

# Run security tests
python manage.py test security.tests
```

### Manual Security Testing

1. **XSS Testing**: Try injecting `<script>alert('XSS')</script>` in input fields
2. **CSRF Testing**: Submit forms without CSRF tokens
3. **SQL Injection Testing**: Try SQL injection patterns in search fields
4. **Authentication Testing**: Access protected endpoints without authentication
5. **File Upload Testing**: Try uploading malicious files

## Security Checklist

### Development

- [ ] All user inputs are validated and sanitized
- [ ] CSRF tokens are included in all forms
- [ ] Authentication is required for protected views
- [ ] Sensitive data is not exposed in responses
- [ ] SQL queries use Django ORM or parameterized queries
- [ ] File uploads are validated
- [ ] Security headers are set
- [ ] Rate limiting is implemented
- [ ] Error messages don't expose sensitive information

### Deployment

- [ ] HTTPS is enabled
- [ ] Security headers are configured
- [ ] Environment variables are set securely
- [ ] Database connections use SSL
- [ ] File permissions are set correctly
- [ ] Logs are monitored for security events
- [ ] Regular security updates are applied
- [ ] Backup and recovery procedures are tested

### Maintenance

- [ ] Regular security audits are performed
- [ ] Dependencies are updated regularly
- [ ] Security logs are reviewed
- [ ] Penetration testing is conducted
- [ ] Security incidents are documented
- [ ] Security training is provided to team

## Incident Response

### Security Incident Response Plan

1. **Detection**: Monitor logs for security events
2. **Assessment**: Evaluate the severity of the incident
3. **Containment**: Isolate affected systems
4. **Eradication**: Remove the threat
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Document and improve

### Contact Information

For security issues:

- **Security Team**: security@nichmah-agrovet.com
- **Emergency Contact**: +254-XXX-XXX-XXX
- **Bug Bounty**: https://nichmah-agrovet.com/security

## Compliance

### Data Protection

- GDPR compliance for EU users
- Data encryption at rest and in transit
- Regular data backups
- Data retention policies

### Industry Standards

- OWASP Top 10 compliance
- ISO 27001 security standards
- PCI DSS for payment processing
- HIPAA for health data (if applicable)

## Resources

### Security Tools

- **Static Analysis**: Bandit, Safety
- **Dynamic Analysis**: OWASP ZAP, Burp Suite
- **Dependency Scanning**: pip-audit, Safety
- **Code Review**: CodeRabbit, SonarQube

### Security References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [Python Security](https://python-security.readthedocs.io/)
- [Security Headers](https://securityheaders.com/)

## Updates

This security documentation is updated regularly. Last updated: December 2024.

For questions or suggestions, contact the security team.

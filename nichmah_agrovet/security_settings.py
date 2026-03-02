"""
Security settings for NICMAH-E Django application.
This module contains all security-related configurations and middleware.
"""

import os
from typing import List, Tuple, Optional

# Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# HTTPS Settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Session Security
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# CSRF Settings
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if os.getenv('CSRF_TRUSTED_ORIGINS') else []

# Content Security Policy
# Allow trusted CDNs for Tailwind CSS, Font Awesome, and Google Fonts
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = (
    "'self'",
    "'unsafe-inline'",  # Required for Tailwind CDN and inline scripts
    "https://cdn.tailwindcss.com",
    "https://cdn.jsdelivr.net",  # For Chart.js used in analytics
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",  # Required for Tailwind CDN and inline styles
    "https://cdn.tailwindcss.com",
    "https://cdnjs.cloudflare.com",
    "https://fonts.googleapis.com",
)
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = (
    "'self'",
    "https://fonts.gstatic.com",
    "https://cdnjs.cloudflare.com",
)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_FORM_ACTION = ("'self'",)
CSP_CONNECT_SRC = (
    "'self'",
    "https://cdn.tailwindcss.com",  # Tailwind CDN may make connections
)

# Rate Limiting
RATE_LIMIT_ENABLED = True
RATE_LIMIT_REQUESTS = 100  # requests per minute
RATE_LIMIT_BLOCK_DURATION = 60  # seconds

# Password Security
# Use PBKDF2 as default (built-in, no extra dependencies)
# Argon2 can be added if django[argon2] or argon2-cffi is installed
try:
    import argon2
    # Argon2 is available, use it as primary
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.Argon2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    ]
except ImportError:
    # Argon2 not available, use PBKDF2 as primary (default Django hasher)
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
        'django.contrib.auth.hashers.Argon2PasswordHasher',  # Keep for when installed
    ]

# Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Security Headers
SECURITY_HEADERS = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}

# Logging Security Events
SECURITY_LOGGING = {
    'SECURITY_EVENTS_LOG': 'logs/security.log',
    'LOG_FAILED_LOGINS': True,
    'LOG_SUSPICIOUS_ACTIVITY': True,
    'LOG_CSRF_FAILURES': True,
}

# Input Validation
INPUT_VALIDATION = {
    'MAX_UPLOAD_SIZE': 10 * 1024 * 1024,  # 10MB
    'ALLOWED_FILE_TYPES': ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx'],
    'SANITIZE_USER_INPUT': True,
    'MAX_INPUT_LENGTH': 1000,
}

# Database Security
DATABASE_SECURITY = {
    'USE_CONNECTION_POOLING': True,
    'MAX_CONNECTIONS': 20,
    'CONNECTION_TIMEOUT': 30,
    'QUERY_TIMEOUT': 60,
}

# API Security
API_SECURITY = {
    'REQUIRE_AUTHENTICATION': True,
    'RATE_LIMIT_ENABLED': True,
    'MAX_REQUESTS_PER_MINUTE': 60,
    'REQUIRE_HTTPS': True,
    'ALLOW_CORS': False,
}

# File Upload Security
FILE_UPLOAD_SECURITY = {
    'MAX_FILE_SIZE': 5 * 1024 * 1024,  # 5MB
    'ALLOWED_EXTENSIONS': ['.jpg', '.jpeg', '.png', '.gif', '.pdf'],
    'SCAN_FOR_VIRUSES': True,
    'STORE_OUTSIDE_WEBROOT': True,
}

# Email Security
EMAIL_SECURITY = {
    'USE_TLS': True,
    'USE_SSL': False,
    'VERIFY_SSL_CERT': True,
    'ALLOW_ATTACHMENTS': False,
}

# Cache Security
CACHE_SECURITY = {
    'USE_SECURE_CACHE_KEYS': True,
    'CACHE_KEY_PREFIX': 'nichmah_',
    'CACHE_TIMEOUT': 3600,  # 1 hour
}

# Monitoring and Alerting
SECURITY_MONITORING = {
    'ENABLE_INTRUSION_DETECTION': True,
    'LOG_SUSPICIOUS_IPS': True,
    'ALERT_ON_FAILED_LOGINS': True,
    'ALERT_ON_ADMIN_ACCESS': True,
}

def get_csp_policy() -> str:
    """Generate Content Security Policy header value."""
    policy_parts = []
    
    if CSP_DEFAULT_SRC:
        policy_parts.append(f"default-src {' '.join(CSP_DEFAULT_SRC)}")
    if CSP_SCRIPT_SRC:
        policy_parts.append(f"script-src {' '.join(CSP_SCRIPT_SRC)}")
    if CSP_STYLE_SRC:
        policy_parts.append(f"style-src {' '.join(CSP_STYLE_SRC)}")
    if CSP_IMG_SRC:
        policy_parts.append(f"img-src {' '.join(CSP_IMG_SRC)}")
    if CSP_FONT_SRC:
        policy_parts.append(f"font-src {' '.join(CSP_FONT_SRC)}")
    if CSP_OBJECT_SRC:
        policy_parts.append(f"object-src {' '.join(CSP_OBJECT_SRC)}")
    if CSP_BASE_URI:
        policy_parts.append(f"base-uri {' '.join(CSP_BASE_URI)}")
    if CSP_FRAME_ANCESTORS:
        policy_parts.append(f"frame-ancestors {' '.join(CSP_FRAME_ANCESTORS)}")
    if CSP_FORM_ACTION:
        policy_parts.append(f"form-action {' '.join(CSP_FORM_ACTION)}")
    if CSP_CONNECT_SRC:
        policy_parts.append(f"connect-src {' '.join(CSP_CONNECT_SRC)}")
    
    return '; '.join(policy_parts)

def get_security_headers() -> List[Tuple[str, str]]:
    """Get list of security headers to be set."""
    headers = []
    
    # Add CSP header
    csp_policy = get_csp_policy()
    if csp_policy:
        headers.append(('Content-Security-Policy', csp_policy))
    
    # Add other security headers
    for header, value in SECURITY_HEADERS.items():
        headers.append((header, value))
    
    return headers

def validate_file_upload(filename: str, file_size: int) -> bool:
    """Validate file upload for security."""
    if file_size > FILE_UPLOAD_SECURITY['MAX_FILE_SIZE']:
        return False
    
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in FILE_UPLOAD_SECURITY['ALLOWED_EXTENSIONS']:
        return False
    
    return True

def sanitize_user_input(input_data: str) -> str:
    """Sanitize user input to prevent XSS."""
    import html
    return html.escape(input_data.strip())

def log_security_event(event_type: str, details: str, user_id: Optional[str] = None, ip_address: Optional[str] = None):
    """Log security events for monitoring."""
    import logging
    from datetime import datetime
    
    security_logger = logging.getLogger('security')
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'details': details,
        'user_id': user_id,
        'ip_address': ip_address,
    }
    
    security_logger.warning(f"SECURITY_EVENT: {log_entry}")

# Security middleware classes
SECURITY_MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'nichmah_agrovet.security_middleware.SecurityHeadersMiddleware',
    'nichmah_agrovet.security_middleware.RateLimitMiddleware',
    'nichmah_agrovet.security_middleware.InputValidationMiddleware',
]

# Security context processors
SECURITY_CONTEXT_PROCESSORS = [
    'nichmah_agrovet.security_context_processors.security_context',
]

# Security template tags
SECURITY_TEMPLATE_TAGS = [
    'nichmah_agrovet.templatetags.security_tags',
]

# Security management commands
SECURITY_MANAGEMENT_COMMANDS = [
    'nichmah_agrovet.management.commands.security_audit',
    'nichmah_agrovet.management.commands.vulnerability_scan',
]

# Security test utilities
SECURITY_TEST_UTILITIES = [
    'nichmah_agrovet.tests.security_test_utils',
]

# Security documentation
SECURITY_DOCUMENTATION = {
    'SECURITY_POLICY': 'docs/SECURITY.md',
    'VULNERABILITY_REPORTING': 'docs/VULNERABILITY_REPORTING.md',
    'SECURITY_CHECKLIST': 'docs/SECURITY_CHECKLIST.md',
}

"""
Enhanced security settings for Django production deployment.
Import this in your main settings.py for production environments.
"""

from decouple import config

# Security Settings
SECURE_BROWSER_XSS_FILTER = config("SECURE_BROWSER_XSS_FILTER", default=True, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = config("SECURE_CONTENT_TYPE_NOSNIFF", default=True, cast=bool)
X_FRAME_OPTIONS = config("X_FRAME_OPTIONS", default="DENY")

# HTTPS Settings (Enable in production)
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=False, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)

# Session Security
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=False, cast=bool)
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# Additional Security Headers
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Content Security Policy (CSP)
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "https:", "data:")

# Rate Limiting (if using django-ratelimit)
RATELIMIT_ENABLE = config("RATELIMIT_ENABLE", default=False, cast=bool)
RATELIMIT_USE_CACHE = "default"

# Logging Security
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "security": {
            "format": "SECURITY: {levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "logs/django.log",
            "formatter": "verbose",
        },
        "security_file": {
            "level": "WARNING",
            "class": "logging.FileHandler",
            "filename": "logs/security.log",
            "formatter": "security",
        },
    },
    "loggers": {
        "django.security": {
            "handlers": ["security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "django": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Password Validation (Enhanced)
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {
            "max_similarity": 0.7,
        },
    },
]

# Login Attempts Limiting
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_ATTEMPT_TIMEOUT = 300  # 5 minutes

# File Upload Security
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5 MB
FILE_UPLOAD_TEMP_DIR = None
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Allowed File Types
ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx", ".xls", ".xlsx"]
ALLOWED_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]

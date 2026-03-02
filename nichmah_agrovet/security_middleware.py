"""
Security middleware for NICMAH-E Django application.
Implements security headers, rate limiting, and input validation.
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional
from django.http import HttpResponse, HttpRequest, QueryDict
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from .security_settings import (
    get_security_headers, 
    validate_file_upload, 
    sanitize_user_input,
    log_security_event
)

logger = logging.getLogger(__name__)

# Module-level XSS patterns (deduplicated for performance)
XSS_PATTERNS = frozenset([
    '<script',
    'javascript:',
    'onload=',
    'onerror=',
    'onclick=',
    'onmouseover=',
    'onfocus=',
    'onblur=',
    'onchange=',
    'oninput=',
    'onkeyup=',
    'onkeydown=',
    'onkeypress=',
    'onmousedown=',
    'onmouseup=',
    'onmouseout=',
    'onmouseenter=',
    'onmouseleave=',
    'onmousemove=',
    'oncontextmenu=',
    'onwheel=',
    'onscroll=',
    'onresize=',
    'onselect=',
    'oncut=',
    'oncopy=',
    'onpaste=',
    'onbeforeunload=',
    'onunload=',
    'onbeforeprint=',
    'onafterprint=',
    'onhashchange=',
    'onmessage=',
    'onoffline=',
    'ononline=',
    'onpagehide=',
    'onpageshow=',
    'onpopstate=',
    'onstorage=',
    'onabort=',
    'onbeforeinput=',
    'oncanplay=',
    'oncanplaythrough=',
    'onclose=',
    'oncuechange=',
    'ondblclick=',
    'ondrag=',
    'ondragend=',
    'ondragenter=',
    'ondragleave=',
    'ondragover=',
    'ondragstart=',
    'ondrop=',
    'ondurationchange=',
    'onemptied=',
    'onended=',
    'onfocusin=',
    'onfocusout=',
    'oninvalid=',
    'onloadeddata=',
    'onloadedmetadata=',
    'onloadstart=',
    'onmousewheel=',
    'onpause=',
    'onplay=',
    'onplaying=',
    'onprogress=',
    'onratechange=',
    'onreset=',
    'onseeked=',
    'onseeking=',
    'onshow=',
    'onstalled=',
    'onsubmit=',
    'onsuspend=',
    'ontimeupdate=',
    'ontoggle=',
    'onvolumechange=',
    'onwaiting=',
])

def get_client_ip(request: HttpRequest) -> str:
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware to add security headers to all responses."""
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers to the response."""
        security_headers = get_security_headers()
        
        for header_name, header_value in security_headers:
            response[header_name] = header_value
        
        return response

class RateLimitMiddleware(MiddlewareMixin):
    """Middleware to implement rate limiting."""
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check rate limits for the request."""
        if not getattr(settings, 'RATE_LIMIT_ENABLED', False):
            return None
        
        # Get client identifier (IP address or user ID)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if self._is_rate_limited(client_id):
            log_security_event(
                'RATE_LIMIT_EXCEEDED',
                f'Rate limit exceeded for {client_id}',
                user_id=getattr(request.user, 'id', None),
                ip_address=get_client_ip(request)
            )
            return HttpResponse(
                'Rate limit exceeded. Please try again later.',
                status=429
            )
        
        # Update rate limit counter
        self._update_rate_limit(client_id)
        return None
    
    def _get_client_id(self, request: HttpRequest) -> str:
        """Get unique client identifier."""
        if request.user.is_authenticated:
            return f"user_{request.user.id}"
        return f"ip_{get_client_ip(request)}"
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        cache_key = f"rate_limit:{client_id}"
        current_count = cache.get(cache_key, 0)
        
        max_requests = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        return current_count >= max_requests
    
    def _update_rate_limit(self, client_id: str) -> None:
        """Update rate limit counter for client using atomic operations."""
        cache_key = f"rate_limit:{client_id}"
        window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)  # seconds
        
        # Atomic increment: try to increment existing key
        try:
            cache.incr(cache_key)
        except ValueError:
            # Key doesn't exist, initialize it atomically
            cache.add(cache_key, 1, window)

class InputValidationMiddleware(MiddlewareMixin):
    """Middleware to validate and sanitize user input."""
    
    def process_request(self, request: HttpRequest) -> Optional[HttpRequest]:
        """Validate and sanitize user input."""
        if not getattr(settings, 'INPUT_VALIDATION', {}).get('SANITIZE_USER_INPUT', False):
            return None
        
        # Sanitize GET parameters
        if request.GET:
            request.GET = self._sanitize_querydict(request.GET)
        
        # Sanitize POST parameters
        if request.POST:
            request.POST = self._sanitize_querydict(request.POST)
        
        # Validate file uploads
        if request.FILES:
            validation_response = self._validate_file_uploads(request)
            if validation_response:
                return validation_response
        
        return None
    
    def _sanitize_querydict(self, querydict) -> Any:
        """Sanitize QueryDict values while preserving multi-valued parameters."""
        sanitized = QueryDict(mutable=True)
        # Use lists() instead of items() to preserve all values for each key
        for key in querydict:
            values = querydict.getlist(key)
            sanitized_values = []
            for value in values:
                if isinstance(value, str):
                    sanitized_values.append(sanitize_user_input(value))
                else:
                    sanitized_values.append(value)
            sanitized.setlist(key, sanitized_values)
        
        return sanitized
    
    def _validate_file_uploads(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Validate file uploads for security. Returns HttpResponse if invalid."""
        for uploaded_file in request.FILES.values():
            if not validate_file_upload(uploaded_file.name, uploaded_file.size):
                log_security_event(
                    'INVALID_FILE_UPLOAD',
                    f'Invalid file upload attempt: {uploaded_file.name}',
                    user_id=getattr(request.user, 'id', None),
                    ip_address=get_client_ip(request)
                )
                return HttpResponse('Invalid file upload', status=400)
        return None

class CSRFProtectionMiddleware(MiddlewareMixin):
    """Enhanced CSRF protection middleware."""
    
    def process_request(self, request: HttpRequest) -> None:
        """Log CSRF failures for monitoring."""
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            if not request.is_secure() and getattr(settings, 'CSRF_COOKIE_SECURE', False):
                log_security_event(
                    'CSRF_INSECURE_REQUEST',
                    'CSRF request made over insecure connection',
                    user_id=getattr(request.user, 'id', None),
                    ip_address=get_client_ip(request)
                )

class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """Middleware to detect potential SQL injection attempts."""
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check for potential SQL injection patterns."""
        suspicious_patterns = [
            'UNION SELECT',
            'DROP TABLE',
            'DELETE FROM',
            'INSERT INTO',
            'UPDATE SET',
            '--',
            '/*',
            '*/',
            'xp_',
            'sp_',
            'WAITFOR',
            'BENCHMARK',
            'SLEEP(',
            'OR 1=1',
            'OR 1=1--',
            'OR 1=1#',
            'OR 1=1/*',
        ]
        
        # Check GET parameters
        for key, value in request.GET.items():
            if isinstance(value, str):
                for pattern in suspicious_patterns:
                    if pattern.lower() in value.lower():
                        self._log_sql_injection_attempt(request, key, value, pattern)
                        return HttpResponse('Invalid input detected', status=400)
        
        # Check POST parameters
        for key, value in request.POST.items():
            if isinstance(value, str):
                for pattern in suspicious_patterns:
                    if pattern.lower() in value.lower():
                        self._log_sql_injection_attempt(request, key, value, pattern)
                        return HttpResponse('Invalid input detected', status=400)
        
        return None
    
    def _log_sql_injection_attempt(self, request: HttpRequest, key: str, value: str, pattern: str) -> None:
        """Log SQL injection attempt."""
        log_security_event(
            'SQL_INJECTION_ATTEMPT',
            f'Potential SQL injection detected: key={key}, pattern={pattern}',
            user_id=getattr(request.user, 'id', None),
            ip_address=get_client_ip(request)
        )

class XSSProtectionMiddleware(MiddlewareMixin):
    """Middleware to detect potential XSS attempts."""
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check for potential XSS patterns."""
        # Check GET parameters
        for key, value in request.GET.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern in XSS_PATTERNS:
                    if pattern.lower() in value_lower:
                        self._log_xss_attempt(request, key, value, pattern)
                        return HttpResponse('Invalid input detected', status=400)
        
        # Check POST parameters
        for key, value in request.POST.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern in XSS_PATTERNS:
                    if pattern.lower() in value_lower:
                        self._log_xss_attempt(request, key, value, pattern)
                        return HttpResponse('Invalid input detected', status=400)
        
        return None
    
    def _log_xss_attempt(self, request: HttpRequest, key: str, value: str, pattern: str) -> None:
        """Log XSS attempt."""
        log_security_event(
            'XSS_ATTEMPT',
            f'Potential XSS detected: key={key}, pattern={pattern}',
            user_id=getattr(request.user, 'id', None),
            ip_address=get_client_ip(request)
        )

class SecurityMonitoringMiddleware(MiddlewareMixin):
    """Middleware to monitor and log security events."""
    
    def process_request(self, request: HttpRequest) -> None:
        """Log suspicious activity."""
        # Log admin access
        if request.path.startswith('/admin/') and request.user.is_authenticated:
            log_security_event(
                'ADMIN_ACCESS',
                f'Admin access: {request.path}',
                user_id=request.user.id,
                ip_address=get_client_ip(request)
            )
        
        # Note: Failed login attempts are now handled by Django signal
        # See nichmah_agrovet.signals for user_login_failed signal handler

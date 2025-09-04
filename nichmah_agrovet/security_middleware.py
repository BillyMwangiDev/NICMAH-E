"""
Security middleware for NICMAH-E Django application.
Implements security headers, rate limiting, and input validation.
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional
from django.http import HttpResponse, HttpRequest
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
                ip_address=self._get_client_ip(request)
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
        return f"ip_{self._get_client_ip(request)}"
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        cache_key = f"rate_limit:{client_id}"
        current_count = cache.get(cache_key, 0)
        
        max_requests = getattr(settings, 'RATE_LIMIT_REQUESTS', 100)
        return current_count >= max_requests
    
    def _update_rate_limit(self, client_id: str) -> None:
        """Update rate limit counter for client."""
        cache_key = f"rate_limit:{client_id}"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, 60)  # 1 minute window

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
            self._validate_file_uploads(request)
        
        return None
    
    def _sanitize_querydict(self, querydict) -> Any:
        """Sanitize QueryDict values."""
        from django.http import QueryDict
        
        sanitized = QueryDict(mutable=True)
        for key, value in querydict.items():
            if isinstance(value, str):
                sanitized_value = sanitize_user_input(value)
                sanitized[key] = sanitized_value
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _validate_file_uploads(self, request: HttpRequest) -> None:
        """Validate file uploads for security."""
        for uploaded_file in request.FILES.values():
            if not validate_file_upload(uploaded_file.name, uploaded_file.size):
                log_security_event(
                    'INVALID_FILE_UPLOAD',
                    f'Invalid file upload attempt: {uploaded_file.name}',
                    user_id=getattr(request.user, 'id', None),
                    ip_address=self._get_client_ip(request)
                )
                raise ValueError(f"Invalid file upload: {uploaded_file.name}")
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

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
                    ip_address=self._get_client_ip(request)
                )
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

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
            ip_address=self._get_client_ip(request)
        )
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

class XSSProtectionMiddleware(MiddlewareMixin):
    """Middleware to detect potential XSS attempts."""
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Check for potential XSS patterns."""
        xss_patterns = [
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
            'onchange=',
            'onclick=',
            'onclose=',
            'oncontextmenu=',
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
            'onerror=',
            'onfocus=',
            'onfocusin=',
            'onfocusout=',
            'oninput=',
            'oninvalid=',
            'onkeydown=',
            'onkeypress=',
            'onkeyup=',
            'onload=',
            'onloadeddata=',
            'onloadedmetadata=',
            'onloadstart=',
            'onmousedown=',
            'onmouseenter=',
            'onmouseleave=',
            'onmousemove=',
            'onmouseout=',
            'onmouseover=',
            'onmouseup=',
            'onmousewheel=',
            'onpause=',
            'onplay=',
            'onplaying=',
            'onprogress=',
            'onratechange=',
            'onreset=',
            'onresize=',
            'onscroll=',
            'onseeked=',
            'onseeking=',
            'onselect=',
            'onshow=',
            'onstalled=',
            'onsubmit=',
            'onsuspend=',
            'ontimeupdate=',
            'ontoggle=',
            'onvolumechange=',
            'onwaiting=',
            'onwheel=',
        ]
        
        # Check GET parameters
        for key, value in request.GET.items():
            if isinstance(value, str):
                for pattern in xss_patterns:
                    if pattern.lower() in value.lower():
                        self._log_xss_attempt(request, key, value, pattern)
                        return HttpResponse('Invalid input detected', status=400)
        
        # Check POST parameters
        for key, value in request.POST.items():
            if isinstance(value, str):
                for pattern in xss_patterns:
                    if pattern.lower() in value.lower():
                        self._log_xss_attempt(request, key, value, pattern)
                        return HttpResponse('Invalid input detected', status=400)
        
        return None
    
    def _log_xss_attempt(self, request: HttpRequest, key: str, value: str, pattern: str) -> None:
        """Log XSS attempt."""
        log_security_event(
            'XSS_ATTEMPT',
            f'Potential XSS detected: key={key}, pattern={pattern}',
            user_id=getattr(request.user, 'id', None),
            ip_address=self._get_client_ip(request)
        )
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

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
                ip_address=self._get_client_ip(request)
            )
        
        # Log failed login attempts
        if request.path.endswith('/login/') and request.method == 'POST':
            if not request.user.is_authenticated:
                log_security_event(
                    'FAILED_LOGIN',
                    f'Failed login attempt from {self._get_client_ip(request)}',
                    ip_address=self._get_client_ip(request)
                )
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

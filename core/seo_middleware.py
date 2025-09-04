"""
SEO Middleware for Nicmah Agrovet website.
Handles basic SEO headers and security headers.
"""

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

try:
    from nichmah_agrovet.seo_settings import SECURITY_HEADERS
except ImportError:
    # Fallback if seo_settings module is not available
    SECURITY_HEADERS = {
        'X-Robots-Tag': 'index, follow',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    }


class SEOMiddleware(MiddlewareMixin):
    """Middleware to add SEO-friendly headers and meta tags."""
    
    def process_response(self, request, response):
        """Add SEO headers and meta tags to response."""
        
        # Add security headers
        for header, value in SECURITY_HEADERS.items():
            response[header] = value
        
        # Add robots.txt header for crawlers
        if 'text/html' in response.get('Content-Type', ''):
            response['X-Robots-Tag'] = 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1'
        
        return response

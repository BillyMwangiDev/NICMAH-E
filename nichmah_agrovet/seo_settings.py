"""
SEO settings for NICMAH website.
Simplified configuration for basic SEO functionality.
"""

# Basic SEO Meta Tags Configuration
SEO_META_TAGS = {
    'default': {
        'title': 'NICMAH - Leading Agricultural Supplies & Services in Kenya',
        'description': 'NICMAH provides quality agricultural supplies, livestock services, crop management solutions, and expert farming advice. Serving farmers across Kenya with trusted agrovet products and services.',
        'keywords': 'agrovet, agricultural supplies, farming equipment, livestock services, crop management, fertilizers, pesticides, seeds, farming tools, Kenya agriculture',
        'author': 'NICMAH',
        'robots': 'index, follow',
        'og_type': 'website',
        'og_title': 'NICMAH - Your Trusted Agricultural Partner',
        'og_description': 'Quality agricultural supplies and expert farming services for Kenyan farmers.',
        'og_image': '/static/images/logo.png',
        'twitter_card': 'summary_large_image',
    }
}

# Security Headers for SEO
SECURITY_HEADERS = {
    'X-Robots-Tag': 'index, follow',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}

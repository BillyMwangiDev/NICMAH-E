"""
Robots.txt URL configuration for SEO.
"""

from django.urls import path
from django.http import HttpResponse
from django.views.decorators.cache import cache_page


@cache_page(60 * 60 * 24)  # Cache for 24 hours
def robots_txt(request):
    """Generate robots.txt content."""
    content = """User-agent: *
Allow: /
Allow: /catalog/
Allow: /educational/
Allow: /about/
Allow: /contact/
Allow: /static/
Allow: /media/

# Disallow admin and private areas
Disallow: /admin/
Disallow: /users/
Disallow: /pos/
Disallow: /inventory/
Disallow: /analytics/
Disallow: /orders/

# Sitemap
Sitemap: https://nicmahagrovet.com/sitemap.xml

# Crawl-delay for respectful crawling
Crawl-delay: 1
"""
    return HttpResponse(content, content_type="text/plain")


urlpatterns = [
    path("", robots_txt, name="robots_txt"),
]




"""
Sitemap configuration for SEO.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone


class StaticViewSitemap(Sitemap):
    """Sitemap for static pages."""
    priority = 0.8
    changefreq = 'monthly'

    def items(self):
        return [
            'core:home',
            'core:about',
            'core:contact',
            'catalog:product_list',
            'educational:article_list',
        ]

    def lastmod(self, item):
        return timezone.now()




from django.contrib.sitemaps import Sitemap
from .models import Article


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Article.objects.filter(is_published=True)

    def lastmod(self, obj: Article):
        return obj.updated_at




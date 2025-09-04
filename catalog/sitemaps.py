from django.contrib.sitemaps import Sitemap
from .models import Product


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj: Product):
        return obj.updated_at if hasattr(obj, "updated_at") else None




"""
URL configuration for nichmah_agrovet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.admin import admin_site
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import StaticViewSitemap
# Sitemap imports simplified

urlpatterns = [
    path("admin/", admin_site.urls),
    path("admin/catalog/", include("catalog.urls", namespace="admin_catalog")),
    path("", include("core.urls")),
    path("users/", include("users.urls")),
    path("catalog/", include("catalog.urls", namespace="catalog")),
    path("orders/", include("orders.urls")),
    path("pos/", include("pos.urls")),
    path("inventory/", include("inventory.urls")),
    path("analytics/", include("analytics.urls")),
    path("educational/", include("educational.urls")),

    path("sitemap.xml", sitemap, {"sitemaps": {
        "static": StaticViewSitemap,
    }}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", include("core.robots_urls")),
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve admin static files
    urlpatterns += static("/admin/", document_root=str(settings.STATIC_ROOT) + "/admin/")

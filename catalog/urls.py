"""
URL configuration for catalog app.
"""

from django.urls import path
from . import views
from . import admin_views

app_name = "catalog"

urlpatterns = [
    # Public URLs
    path("", views.product_list, name="product_list"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    path("search/", views.quick_search, name="quick_search"),
    path("search-suggestions/", views.search_suggestions, name="search_suggestions"),
    path("api/products/search/", views.api_product_search, name="api_product_search"),
    
    # Admin URLs
    path("quick-upload-image/", admin_views.quick_upload_image, name="admin_quick_upload_image"),
]

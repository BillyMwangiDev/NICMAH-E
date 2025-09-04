"""
URL configuration for analytics app.
"""

from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sales-report/", views.sales_report, name="sales_report"),
    path("export-sales/", views.export_sales_data, name="export_sales_data"),
    path("seller-dashboard/", views.seller_dashboard, name="seller_dashboard"),
]

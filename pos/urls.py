"""
URL configuration for POS app.
"""

from django.urls import path
from . import views

app_name = "pos"

urlpatterns = [
    path("", views.pos_dashboard, name="dashboard"),
    path("sale/create/", views.pos_sale_create, name="sale_create"),
    path("sale/<int:sale_id>/", views.pos_sale_detail, name="sale_detail"),
    path("session/<int:session_id>/close/", views.pos_session_close, name="session_close"),
    path("sales/", views.pos_sales_list, name="sales_list"),
    path("barcode/scan/", views.pos_barcode_scan, name="barcode_scan"),
    path("product/search/", views.pos_product_search, name="product_search"),
    path("discount/apply/", views.pos_discount_apply, name="discount_apply"),
    path("receipt/<int:sale_id>/download/", views.pos_receipt_download, name="receipt_download"),
    path("analytics/", views.pos_analytics, name="analytics"),
    # Offline functionality URLs
    path("offline/toggle/", views.toggle_offline_mode, name="toggle_offline_mode"),
    path("offline/sync/", views.sync_offline_transactions, name="sync_offline_transactions"),
    path("offline/transactions/", views.offline_transactions_list, name="offline_transactions_list"),
    path("offline/sale/create/", views.offline_sale_create, name="offline_sale_create"),
    path("connection/status/", views.check_connection_status, name="check_connection_status"),
    # Receipt printer endpoints
    path("receipt/<int:sale_id>/print/", views.pos_receipt_print, name="receipt_print"),
    path("printer/test/", views.pos_printer_test, name="printer_test"),
    path("printer/list/", views.pos_printer_list, name="printer_list"),
]

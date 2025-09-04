"""
URL configuration for inventory app.
"""

from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("sku-scanner/", views.sku_scanner, name="sku_scanner"),
    path("quick-receiving/", views.quick_stock_receiving, name="quick_stock_receiving"),
    path("record-purchase/", views.record_purchase, name="record_purchase"),
    path("stock-movements/", views.stock_movements, name="stock_movements"),
    path("export-stock/", views.export_stock_data, name="export_stock_data"),
    path("import-stock/", views.import_stock_data, name="import_stock_data"),
    path("export-movements/", views.export_stock_movements, name="export_stock_movements"),
    path("alerts/", views.stock_alerts, name="stock_alerts"),
    path("alerts/json/", views.stock_alerts_json, name="stock_alerts_json"),
    path("alerts/<str:alert_id>/acknowledge/", views.acknowledge_alert, name="acknowledge_alert"),
    path("alerts/<str:alert_id>/resolve/", views.resolve_alert, name="resolve_alert"),
    path("purchase-orders/", views.purchase_orders, name="purchase_orders"),
    path("stock-management/", views.stock_management, name="stock_management"),
    
    # Document generation URLs
    path("documents/", views.inventory_documents, name="documents"),
    path("documents/generate-receipt/", views.generate_receipt_from_stock, name="generate_receipt"),
    path("documents/generate-receipt/<int:movement_id>/", views.generate_receipt_from_stock, name="generate_receipt_from_stock"),
    path("documents/generate-quotation/", views.generate_quotation_from_products, name="generate_quotation_from_products"),
    path("documents/generate-invoice/", views.generate_invoice, name="generate_invoice"),
    path("documents/generate-purchase-order/", views.generate_purchase_order, name="generate_purchase_order"),

    path("documents/<int:pk>/", views.view_document, name="view_document"),
    path("documents/<int:pk>/pdf/", views.download_document_pdf, name="download_document_pdf"),
    path("documents/<int:pk>/email/", views.email_document, name="email_document"),
    path("documents/<int:pk>/print/", views.print_document_view, name="print_document"),
]

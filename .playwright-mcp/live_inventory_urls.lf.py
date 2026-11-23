from django.urls import path
from .views import (
    ProductListView,
    ProductDetailView,
    ProductSlugDetailView,
    FeaturedProductsView,
    ProductSearchSuggestionsView,
    CategoryListView,
    CategoryDetailView,
    InventoryAdminListView,
    ProductAdminDetailView,
    StockAdjustView,
    StockLogView,
    ExcelImportView,
    ExcelExportView,
    # Phase 3: Suppliers
    SupplierListCreateView,
    SupplierDetailView,
    # Phase 3: Purchase Orders
    PurchaseOrderListCreateView,
    PurchaseOrderDetailView,
    PurchaseOrderReceiveView,
    # Phase 3: Stock Alerts
    StockAlertListView,
    StockAlertAcknowledgeView,
    StockAlertResolveView,
    StockAlertGenerateView,
    # PO PDF
    PurchaseOrderPDFView,
)

urlpatterns = [
    # Public endpoints
    path("products/", ProductListView.as_view(), name="product_list"),
    path("products/featured/", FeaturedProductsView.as_view(), name="featured_products"),
    path("products/search/", ProductSearchSuggestionsView.as_view(), name="product_search_suggestions"),
    path("products/slug/<slug:slug>/", ProductSlugDetailView.as_view(), name="product_detail_slug"),
    path("products/<uuid:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("categories/", CategoryListView.as_view(), name="category_list"),
    path("categories/<slug:slug>/", CategoryDetailView.as_view(), name="category_detail"),
    # Admin-only inventory endpoints
    path("admin/inventory/", InventoryAdminListView.as_view(), name="inventory_admin"),
    path("admin/inventory/<uuid:pk>/", ProductAdminDetailView.as_view(), name="inventory_admin_detail"),
    path("admin/inventory/<uuid:pk>/adjust-stock/", StockAdjustView.as_view(), name="stock_adjust"),
    path("admin/inventory/<uuid:pk>/stock-log/", StockLogView.as_view(), name="stock_log"),
    path("admin/import-excel/", ExcelImportView.as_view(), name="excel_import"),
    path("admin/export-excel/", ExcelExportView.as_view(), name="excel_export"),
    # Suppliers
    path("suppliers/", SupplierListCreateView.as_view(), name="supplier_list"),
    path("suppliers/<uuid:pk>/", SupplierDetailView.as_view(), name="supplier_detail"),
    # Purchase Orders
    path("purchase-orders/", PurchaseOrderListCreateView.as_view(), name="purchase_order_list"),
    path("purchase-orders/<uuid:pk>/", PurchaseOrderDetailView.as_view(), name="purchase_order_detail"),
    path("purchase-orders/<uuid:pk>/receive/", PurchaseOrderReceiveView.as_view(), name="purchase_order_receive"),
    path("purchase-orders/<uuid:pk>/pdf/", PurchaseOrderPDFView.as_view(), name="purchase_order_pdf"),
    # Stock Alerts
    path("stock-alerts/", StockAlertListView.as_view(), name="stock_alert_list"),
    path("stock-alerts/generate/", StockAlertGenerateView.as_view(), name="stock_alert_generate"),
    path("stock-alerts/<uuid:pk>/acknowledge/", StockAlertAcknowledgeView.as_view(), name="stock_alert_acknowledge"),
    path("stock-alerts/<uuid:pk>/resolve/", StockAlertResolveView.as_view(), name="stock_alert_resolve"),
]

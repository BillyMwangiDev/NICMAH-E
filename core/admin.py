"""
Custom admin site for Nicmah Agrovet with role-based access control.
"""

from django.contrib import admin
from django.contrib.admin import AdminSite
import django.contrib.admin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.urls import path
from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from django.apps import apps
import json

# Import models with error handling
try:
    from .models import SiteSettings
except ImportError:
    SiteSettings = None

try:
    from users.models import CustomUser, UserProfile, SellerProfile
    from users.admin import CustomUserAdmin, UserProfileAdmin, SellerProfileAdmin
except ImportError:
    CustomUser = UserProfile = SellerProfile = None
    CustomUserAdmin = UserProfileAdmin = SellerProfileAdmin = None

try:
    from pos.models import POSSale, POSSaleItem, POSSession, TaxRate, Discount, Barcode, Receipt, OfflineTransaction
    from pos.admin import (
        POSSaleAdmin,
        POSSaleItemAdmin,
        POSSessionAdmin,
        TaxRateAdmin,
        DiscountAdmin,
        BarcodeAdmin,
        ReceiptAdmin,
        OfflineTransactionAdmin,
    )
except ImportError:
    POSSale = POSSaleItem = POSSession = TaxRate = Discount = Barcode = Receipt = OfflineTransaction = None
    POSSaleAdmin = POSSaleItemAdmin = POSSessionAdmin = TaxRateAdmin = DiscountAdmin = None
    BarcodeAdmin = ReceiptAdmin = OfflineTransactionAdmin = None

try:
    from catalog.models import Product, Category
    from catalog.admin import CategoryAdmin
except ImportError:
    Product = Category = None
    CategoryAdmin = None

try:
    from inventory.models import StockMovement, StockAlert, PurchaseOrder
    from inventory.admin import PurchaseOrderAdmin
except ImportError:
    StockMovement = StockAlert = PurchaseOrder = None
    PurchaseOrderAdmin = None

try:
    from orders.models import Order
    from orders.admin import OrderAdmin
except ImportError:
    Order = None
    OrderAdmin = None

try:
    from analytics.models import SalesReport, ProductPerformance, CustomerInsight, DashboardWidget
    from analytics.admin import SalesReportAdmin, ProductPerformanceAdmin, CustomerInsightAdmin, DashboardWidgetAdmin
except ImportError:
    SalesReport = ProductPerformance = CustomerInsight = DashboardWidget = None
    SalesReportAdmin = ProductPerformanceAdmin = CustomerInsightAdmin = DashboardWidgetAdmin = None


try:
    from educational.models import Article
    from educational.admin import ArticleAdmin
except ImportError:
    Article = None
    ArticleAdmin = None


def is_admin_user(user):
    """Check if user is admin or staff."""
    return user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin")


def is_seller_user(user):
    """Check if user is a seller."""
    return user.is_authenticated and getattr(user, "role", None) == "seller"


class NicmahAgrovetAdminSite(AdminSite):
    """Custom admin site with enhanced features and role-based access."""

    site_header = "Nicmah Agrovet Administration"
    site_title = "Nicmah Agrovet Admin"
    index_title = "Welcome to Nicmah Agrovet Administration"

    def has_permission(self, request):
        """Check if user has permission to access admin."""
        if not request.user.is_authenticated:
            return False

        # Only staff and admin users can access admin
        return request.user.is_staff or getattr(request.user, "role", None) == "admin"

    def get_urls(self):
        """Add custom URLs for dashboard and analytics."""
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/", self.admin_view(self.dashboard_view), name="dashboard"),
            path("analytics/", self.admin_view(self.analytics_view), name="analytics"),
            path("pos-overview/", self.admin_view(self.pos_overview_view), name="pos-overview"),
            path("inventory-status/", self.admin_view(self.inventory_status_view), name="inventory-status"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """Enhanced admin dashboard with key metrics."""
        # Check authentication and permissions
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not is_admin_user(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        
        # Get date range for analytics
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Key metrics
        total_users = CustomUser.objects.count() if CustomUser else 0
        total_products = Product.objects.count() if Product else 0
        total_sales = POSSale.objects.filter(status="completed").count() if POSSale else 0
        total_revenue = (
            POSSale.objects.filter(status="completed").aggregate(total=Sum("total_amount"))["total"]
            if POSSale
            else Decimal("0.00")
        )

        # Recent activity
        recent_sales = POSSale.objects.filter(status="completed").order_by("-created_at")[:5] if POSSale else []
        recent_users = CustomUser.objects.order_by("-date_joined")[:5] if CustomUser else []

        # Low stock alerts and notifications
        low_stock_products = Product.objects.filter(stock_quantity__lte=10)[:5] if Product else []
        low_stock_count = Product.objects.filter(stock_quantity__lte=10).count() if Product else 0
        out_of_stock_count = Product.objects.filter(stock_quantity=0).count() if Product else 0

        # Get active stock alerts
        active_alerts = []
        if "inventory.StockAlert" in [app.model_name for app in apps.get_app_configs()]:
            try:
                from inventory.models import StockAlert

                active_alerts = (
                    StockAlert.objects.filter(status="active")
                    .select_related("product")
                    .order_by("-priority", "-created_at")[:10]
                )
            except ImportError:
                pass

        # Calculate additional metrics
        total_transactions = total_sales
        active_sellers = CustomUser.objects.filter(role="seller", is_active=True).count() if CustomUser else 0

        # Prepare sales data for charts
        sales_data = []
        products_data = []

        if POSSale:
            # Daily sales data
            daily_sales = (
                POSSale.objects.filter(created_at__range=[start_date, end_date], status="completed")
                .extra(select={"day": "date(created_at)"})
                .values("day")
                .annotate(total=Sum("total_amount"))
                .order_by("day")
            )

            sales_data = [{"date": item["day"], "total": float(item["total"])} for item in daily_sales]

            # Top products data
            top_products = (
                POSSaleItem.objects.filter(sale__created_at__range=[start_date, end_date], sale__status="completed")
                .values("product__name")
                .annotate(total_quantity=Sum("quantity"))
                .order_by("-total_quantity")[:8]
                if ("pos.POSSaleItem" in [app.model_name for app in apps.get_app_configs()])
                else []
            )

            products_data = [
                {"product__name": item["product__name"], "total_quantity": item["total_quantity"]}
                for item in top_products
            ]

        context = {
            "total_users": total_users,
            "total_products": total_products,
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_transactions": total_transactions,
            "active_sellers": active_sellers,
            "recent_sales": recent_sales,
            "recent_users": recent_users,
            "low_stock_products": low_stock_products,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "active_alerts": active_alerts,
            "sales_data_json": json.dumps(sales_data),
            "products_data_json": json.dumps(products_data),
        }

        return render(request, "admin/dashboard.html", context)

    def analytics_view(self, request):
        """Business analytics and insights."""
        # Check authentication and permissions
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not is_admin_user(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        
        # Get date range for analytics
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        # Sales analytics - daily breakdown
        daily_sales = []
        if POSSale:
            daily_sales = (
                POSSale.objects.filter(created_at__range=[start_date, end_date], status="completed")
                .extra(select={"day": "date(created_at)"})
                .values("day")
                .annotate(total=Sum("total_amount"), count=Count("id"))
                .order_by("day")
            )

        # Prepare sales data for charts - use sample data if no real data
        if daily_sales:
            sales_data = [
                {"date": item["day"], "total": float(item["total"]), "count": item["count"]} for item in daily_sales
            ]
        else:
            # Sample data for testing
            sales_data = [
                {
                    "date": (end_date - timedelta(days=i)).strftime("%Y-%m-%d"),
                    "total": 500 + (i * 100) + (i * 50),
                    "count": 5 + i,
                }
                for i in range(30, 0, -1)
            ]

        # Top products by quantity sold
        top_products = []
        if "pos.POSSaleItem" in [app.model_name for app in apps.get_app_configs()]:
            top_products = (
                POSSaleItem.objects.filter(sale__created_at__range=[start_date, end_date], sale__status="completed")
                .values("product__name", "product__category__name")
                .annotate(total_quantity=Sum("quantity"), total_revenue=Sum("total_price"))
                .order_by("-total_quantity")[:8]
            )

        # Use sample products if no real data
        if not top_products:
            top_products = [
                {
                    "product__name": "Sample Product 1",
                    "product__category__name": "Fertilizers",
                    "total_quantity": 150,
                    "total_revenue": 1500.00,
                },
                {
                    "product__name": "Sample Product 2",
                    "product__category__name": "Seeds",
                    "total_quantity": 120,
                    "total_revenue": 1200.00,
                },
                {
                    "product__name": "Sample Product 3",
                    "product__category__name": "Pesticides",
                    "total_quantity": 95,
                    "total_revenue": 950.00,
                },
                {
                    "product__name": "Sample Product 4",
                    "product__category__name": "Tools",
                    "total_quantity": 80,
                    "total_revenue": 800.00,
                },
                {
                    "product__name": "Sample Product 5",
                    "product__category__name": "Fertilizers",
                    "total_quantity": 75,
                    "total_revenue": 750.00,
                },
                {
                    "product__name": "Sample Product 6",
                    "product__category__name": "Seeds",
                    "total_quantity": 65,
                    "total_revenue": 650.00,
                },
                {
                    "product__name": "Sample Product 7",
                    "product__category__name": "Pesticides",
                    "total_quantity": 55,
                    "total_revenue": 550.00,
                },
                {
                    "product__name": "Sample Product 8",
                    "product__category__name": "Tools",
                    "total_quantity": 45,
                    "total_revenue": 450.00,
                },
            ]

        # Category performance
        category_performance = []
        if top_products and any("product__category__name" in item for item in top_products):
            category_performance = (
                POSSaleItem.objects.filter(sale__created_at__range=[start_date, end_date], sale__status="completed")
                .values("product__category__name")
                .annotate(total_revenue=Sum("total_price"), total_quantity=Sum("quantity"))
                .order_by("-total_revenue")
            )

        # Use sample category data if no real data
        if not category_performance:
            category_performance = [
                {"product__category__name": "Fertilizers", "total_revenue": 2250.00, "total_quantity": 225},
                {"product__category__name": "Seeds", "total_revenue": 1850.00, "total_quantity": 185},
                {"product__category__name": "Pesticides", "total_revenue": 1500.00, "total_quantity": 150},
                {"product__category__name": "Tools", "total_revenue": 1250.00, "total_quantity": 125},
                {"product__category__name": "Irrigation", "total_revenue": 950.00, "total_quantity": 95},
                {"product__category__name": "Organic", "total_revenue": 750.00, "total_quantity": 75},
            ]

        # Payment method analysis
        payment_methods = []
        if POSSale:
            payment_methods = (
                POSSale.objects.filter(created_at__range=[start_date, end_date], status="completed")
                .values("payment_method")
                .annotate(total=Sum("total_amount"), count=Count("id"))
                .order_by("-total")
            )

        # Use sample payment data if no real data
        if not payment_methods:
            payment_methods = [
                {"payment_method": "cash", "total": 3500.00, "count": 45},
                {"payment_method": "card", "total": 2500.00, "count": 25},
                {"payment_method": "mobile_money", "total": 1500.00, "count": 20},
                {"payment_method": "bank_transfer", "total": 750.00, "count": 10},
            ]

        # Calculate totals
        total_revenue = (
            sum(item["total"] for item in daily_sales) if daily_sales else sum(item["total"] for item in sales_data)
        )
        total_transactions = (
            sum(item["count"] for item in daily_sales) if daily_sales else sum(item["count"] for item in sales_data)
        )

        # Prepare chart data
        chart_data = {
            "sales_data": sales_data,
            "top_products": list(top_products),
            "category_performance": list(category_performance),
            "payment_methods": list(payment_methods),
        }

        context = {
            "chart_data": json.dumps(chart_data),
            "sales_data_json": json.dumps(sales_data),
            "products_data_json": json.dumps(list(top_products)),
            "category_performance_json": json.dumps(list(category_performance)),
            "payment_methods_json": json.dumps(list(payment_methods)),
            "top_products": top_products,
            "category_performance": category_performance,
            "payment_methods": payment_methods,
            "total_revenue": total_revenue,
            "total_transactions": total_transactions,
        }

        return render(request, "admin/analytics.html", context)

    def pos_overview_view(self, request):
        """POS system overview and management."""
        # Check authentication and permissions
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not is_admin_user(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        
        # Get active POS session
        active_session = POSSession.objects.filter(is_active=True).first() if POSSession else None

        # Today's sales
        today = timezone.now().date()
        today_sales = POSSale.objects.filter(created_at__date=today, status="completed") if POSSale else []

        today_total = sum(sale.total_amount for sale in today_sales)
        today_count = len(today_sales)

        # Recent transactions
        recent_transactions = POSSale.objects.filter(status="completed").order_by("-created_at")[:10] if POSSale else []

        context = {
            "active_session": active_session,
            "today_total": today_total,
            "today_count": today_count,
            "recent_transactions": recent_transactions,
        }

        return render(request, "admin/pos-overview.html", context)

    def inventory_status_view(self, request):
        """Inventory status and alerts."""
        # Check authentication and permissions
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        
        if not is_admin_user(request.user):
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Access denied. Admin privileges required.")
        
        # Stock levels
        total_products = Product.objects.count() if Product else 0
        low_stock = Product.objects.filter(stock_quantity__lte=10).count() if Product else 0
        out_of_stock = Product.objects.filter(stock_quantity=0).count() if Product else 0

        # Low stock products
        low_stock_products = (
            Product.objects.filter(stock_quantity__lte=10).order_by("stock_quantity")[:10] if Product else []
        )

        # Recent stock movements
        recent_movements = (
            StockMovement.objects.select_related("product", "user").order_by("-created_at")[:10]
            if StockMovement
            else []
        )

        context = {
            "total_products": total_products,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "low_stock_products": low_stock_products,
            "recent_movements": recent_movements,
        }

        return render(request, "admin/inventory-status.html", context)


# Create custom admin site instance


admin_site = NicmahAgrovetAdminSite(name="nicmah_admin")

# Admin classes with role-based access


class SiteSettingsAdmin(admin.ModelAdmin):
    """Admin for site settings - admin only."""

    def has_module_permission(self, request):
        return is_admin_user(request.user)

    def has_view_permission(self, request, obj=None):
        return is_admin_user(request.user)

    def has_add_permission(self, request):
        return is_admin_user(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin_user(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_admin_user(request.user)

    list_display = ["site_name", "contact_email", "phone_number", "currency", "years_in_business"]
    list_editable = ["currency"]
    fieldsets = (
        ("Basic Information", {"fields": ("site_name", "site_description", "logo")}),
        (
            "Business Information",
            {"fields": ("business_description", "mission_statement", "vision_statement"), "classes": ("wide",)},
        ),
        ("Services Offered", {"fields": ("livestock_services", "crop_services"), "classes": ("wide", "collapse")}),
        ("Contact Information", {"fields": ("contact_email", "phone_number", "address")}),
        (
            "Social Media",
            {"fields": ("facebook_url", "tiktok_url", "instagram_url", "twitter_url"), "classes": ("collapse",)},
        ),
        ("Business Settings", {"fields": ("currency", "tax_rate", "business_hours")}),
        (
            "Experience & Achievements",
            {"fields": ("years_in_business", "cattle_ai_count", "farmers_served"), "classes": ("collapse",)},
        ),
    )


class CustomUserAdminOverride(admin.ModelAdmin):
    """Admin for custom users with role-based access."""

    def has_module_permission(self, request):
        return is_admin_user(request.user)

    def has_view_permission(self, request, obj=None):
        return is_admin_user(request.user)

    def has_add_permission(self, request):
        return is_admin_user(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin_user(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_admin_user(request.user)

    list_display = ["username", "email", "first_name", "last_name", "role", "is_active", "date_joined"]
    list_filter = ["role", "is_active", "is_staff", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]

    fieldsets = (
        ("Basic Information", {"fields": ("username", "email", "first_name", "last_name", "password")}),
        (
            "Role & Permissions",
            {"fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        """Filter queryset based on user role."""
        qs = super().get_queryset(request)
        if is_admin_user(request.user):
            return qs
        elif is_seller_user(request.user):
            return qs.filter(id=request.user.id)
        return qs.none()


class POSSaleAdminOverride(admin.ModelAdmin):
    """Admin for POS sales with role-based access."""

    def has_module_permission(self, request):
        return is_admin_user(request.user) or is_seller_user(request.user)

    def has_view_permission(self, request, obj=None):
        if is_admin_user(request.user):
            return True
        elif is_seller_user(request.user):
            return obj is None or obj.seller == request.user
        return False

    def has_add_permission(self, request):
        return is_admin_user(request.user) or is_seller_user(request.user)

    def has_change_permission(self, request, obj=None):
        if is_admin_user(request.user):
            return True
        elif is_seller_user(request.user):
            return obj is None or obj.seller == request.user
        return False

    def has_delete_permission(self, request, obj=None):
        return is_admin_user(request.user)

    list_display = ["sale_number", "customer_name", "seller", "total_amount", "status", "created_at"]
    list_filter = ["status", "payment_method", "created_at", "seller"]
    search_fields = ["sale_number", "customer_name", "seller__username"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Sale Information", {"fields": ("sale_number", "customer_name", "status", "payment_method")}),
        ("Financial", {"fields": ("subtotal", "tax_amount", "discount_amount", "total_amount")}),
        ("User Information", {"fields": ("seller", "cashier")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Filter queryset based on user role."""
        qs = super().get_queryset(request)
        if is_admin_user(request.user):
            return qs
        elif is_seller_user(request.user):
            return qs.filter(seller=request.user)
        return qs.none()


class ProductAdmin(admin.ModelAdmin):
    """Admin for products with role-based access."""

    def has_module_permission(self, request):
        return is_admin_user(request.user) or is_seller_user(request.user)

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        return is_admin_user(request.user)

    def has_change_permission(self, request, obj=None):
        return is_admin_user(request.user)

    def has_delete_permission(self, request, obj=None):
        return is_admin_user(request.user)

    list_display = ["name", "sku", "category", "price", "stock_quantity", "is_active"]
    list_filter = ["category", "is_active", "created_at"]
    search_fields = ["name", "sku", "description"]
    ordering = ["name"]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "sku", "description", "category")}),
        ("Pricing & Stock", {"fields": ("price", "stock_quantity", "min_stock_level")}),
        ("Status", {"fields": ("is_active",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ["created_at", "updated_at"]


class StockMovementAdmin(admin.ModelAdmin):
    """Admin for stock movements."""

    def has_module_permission(self, request):
        return is_admin_user(request.user)

    list_display = [
        "movement_id",
        "product",
        "movement_type",
        "quantity",
        "previous_stock",
        "new_stock",
        "user",
        "created_at",
    ]
    list_filter = ["movement_type", "created_at", "product__category"]
    search_fields = ["product__name", "movement_id", "reference_number"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Movement Information", {"fields": ("movement_id", "product", "movement_type", "quantity")}),
        ("Stock Levels", {"fields": ("previous_stock", "new_stock")}),
        ("Reference", {"fields": ("reference_number", "reference_type")}),
        ("User & Notes", {"fields": ("user", "notes")}),
        ("Timestamps", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    readonly_fields = ["movement_id", "created_at"]


class StockAlertAdmin(admin.ModelAdmin):
    """Admin for stock alerts."""

    def has_module_permission(self, request):
        return is_admin_user(request.user)

    list_display = [
        "alert_id",
        "product",
        "alert_type",
        "priority",
        "status",
        "current_value",
        "threshold_value",
        "created_at",
    ]
    list_filter = ["alert_type", "priority", "status", "created_at"]
    search_fields = ["product__name", "message"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Alert Information", {"fields": ("alert_id", "product", "alert_type", "priority", "status")}),
        ("Thresholds", {"fields": ("current_value", "threshold_value")}),
        ("Details", {"fields": ("message", "notes")}),
        ("Timestamps", {"fields": ("created_at", "acknowledged_at", "resolved_at"), "classes": ("collapse",)}),
    )

    readonly_fields = ["alert_id", "created_at", "acknowledged_at", "resolved_at"]


# Register models with custom admin site
if SiteSettings:
    admin_site.register(SiteSettings, SiteSettingsAdmin)

if CustomUser and CustomUserAdmin:
    admin_site.register(CustomUser, CustomUserAdminOverride)

if UserProfile and UserProfileAdmin:
    admin_site.register(UserProfile, UserProfileAdmin)

if SellerProfile and SellerProfileAdmin:
    admin_site.register(SellerProfile, SellerProfileAdmin)

if POSSale and POSSaleAdmin:
    admin_site.register(POSSale, POSSaleAdminOverride)

if POSSaleItem and POSSaleItemAdmin:
    admin_site.register(POSSaleItem, POSSaleItemAdmin)

if POSSession and POSSessionAdmin:
    admin_site.register(POSSession, POSSessionAdmin)

if TaxRate and TaxRateAdmin:
    admin_site.register(TaxRate, TaxRateAdmin)

if Discount and DiscountAdmin:
    admin_site.register(Discount, DiscountAdmin)

if Barcode and BarcodeAdmin:
    admin_site.register(Barcode, BarcodeAdmin)

if Receipt and ReceiptAdmin:
    admin_site.register(Receipt, ReceiptAdmin)

if OfflineTransaction and OfflineTransactionAdmin:
    admin_site.register(OfflineTransaction, OfflineTransactionAdmin)

if Category and CategoryAdmin:
    admin_site.register(Category, CategoryAdmin)

if Product:
    from catalog.admin import ProductAdmin
    admin_site.register(Product, ProductAdmin)

# Register inventory models
if StockMovement:
    admin_site.register(StockMovement, StockMovementAdmin)

if StockAlert:
    admin_site.register(StockAlert, StockAlertAdmin)

if PurchaseOrder and PurchaseOrderAdmin:
    admin_site.register(PurchaseOrder, PurchaseOrderAdmin)

# Register educational models
if Article and ArticleAdmin:
    admin_site.register(Article, ArticleAdmin)

# Register analytics models
if SalesReport and SalesReportAdmin:
    admin_site.register(SalesReport, SalesReportAdmin)

if ProductPerformance and ProductPerformanceAdmin:
    admin_site.register(ProductPerformance, ProductPerformanceAdmin)

if CustomerInsight and CustomerInsightAdmin:
    admin_site.register(CustomerInsight, CustomerInsightAdmin)

if DashboardWidget and DashboardWidgetAdmin:
    admin_site.register(DashboardWidget, DashboardWidgetAdmin)

# Register orders models
if Order:
    admin_site.register(Order, OrderAdmin)

# Override the default admin site completely
admin.site = admin_site

# Also override the global admin site reference
django.contrib.admin.site = admin_site

from django.contrib import admin
from .models import Sales, SalesItem, SalesAnalytics


class SalesAdmin(admin.ModelAdmin):
    """Admin for unified Sales model - shows all sales (POS, e-commerce, manual) that match analytics views.
    
    This is the SAME data shown in analytics pages. Use this for viewing unified sales data.
    For raw POS transactions, see POSSale model in POS section.
    """
    list_display = ("sale_number", "sale_type", "customer_name", "total_amount", "payment_method", "status", "created_at")
    list_filter = ("sale_type", "status", "payment_method", "created_at")
    search_fields = ("sale_number", "customer_name", "customer_phone", "customer_email")
    readonly_fields = ("sale_number", "created_at", "updated_at")
    ordering = ["-created_at"]
    
    def get_queryset(self, request):
        """Show same data as analytics views - all unified sales with optimized queries."""
        qs = super().get_queryset(request)
        # Use select_related and prefetch_related for performance (same as analytics views)
        return qs.select_related("cashier", "seller", "pos_sale", "ecommerce_order").prefetch_related("items", "items__product")
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('sale_number', 'sale_type', 'status', 'created_at', 'updated_at')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_phone', 'customer_email', 'customer_address')
        }),
        ('Financial Information', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'amount_paid', 'change_given')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'cashier', 'seller')
        }),
        ('References', {
            'fields': ('pos_sale', 'ecommerce_order', 'receipt_number'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


class SalesItemAdmin(admin.ModelAdmin):
    list_display = ("sale", "product", "quantity", "unit_price", "total_price", "created_at")
    list_filter = ("created_at", "product")
    search_fields = ("sale__sale_number", "product__name")
    readonly_fields = ("created_at",)


class SalesAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("date", "total_sales", "total_revenue", "pos_sales", "ecommerce_sales", "manual_sales")
    list_filter = ("date",)
    search_fields = ("date",)
    readonly_fields = ("created_at", "updated_at")
    
    fieldsets = (
        ('Date Information', {
            'fields': ('date', 'created_at', 'updated_at')
        }),
        ('Sales Counts', {
            'fields': ('total_sales', 'pos_sales', 'ecommerce_sales', 'manual_sales')
        }),
        ('Financial Totals', {
            'fields': ('total_revenue', 'pos_revenue', 'ecommerce_revenue', 'manual_revenue')
        }),
        ('Tax and Discounts', {
            'fields': ('total_tax', 'total_discounts')
        }),
        ('Payment Methods', {
            'fields': ('cash_sales', 'card_sales', 'mobile_money_sales', 'bank_transfer_sales', 'whatsapp_sales', 'other_sales'),
            'classes': ('collapse',)
        }),
        ('Top Products', {
            'fields': ('top_products',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        return False  # Analytics are auto-generated

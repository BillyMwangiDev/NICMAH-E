"""
Admin interface for POS models.
"""

from django.contrib import admin

from .models import POSSession, POSSale, POSSaleItem, Receipt, Barcode, TaxRate, Discount, OfflineTransaction


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = ["name", "rate", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ["name", "discount_type", "percentage_rate", "fixed_amount", "is_active", "start_date", "end_date"]
    list_filter = ["discount_type", "is_active", "start_date", "end_date"]
    search_fields = ["name", "description"]
    ordering = ["-created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()


@admin.register(Barcode)
class BarcodeAdmin(admin.ModelAdmin):
    list_display = ["barcode", "product", "barcode_type", "is_active", "created_at"]
    list_filter = ["barcode_type", "is_active", "created_at"]
    search_fields = ["barcode", "product__name", "product__sku"]
    ordering = ["barcode"]


@admin.register(POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = [
        "session_id",
        "cashier",
        "seller",
        "status",
        "total_sales",
        "total_transactions",
        "opened_at",
        "is_offline",
    ]
    list_filter = ["status", "is_offline", "sync_status", "opened_at", "closed_at"]
    search_fields = ["session_id", "cashier__username", "cashier__first_name", "seller__username"]
    readonly_fields = ["session_id", "opened_at", "updated_at"]
    ordering = ["-opened_at"]

    fieldsets = (
        ("Session Information", {"fields": ("session_id", "cashier", "seller", "status")}),
        ("Financial Tracking", {"fields": ("opening_amount", "closing_amount", "total_sales", "total_transactions")}),
        (
            "Payment Breakdown",
            {
                "fields": (
                    "total_tax_collected",
                    "total_discounts_given",
                    "total_cash_sales",
                    "total_card_sales",
                    "total_mobile_money",
                )
            },
        ),
        (
            "Offline Functionality",
            {"fields": ("is_offline", "offline_start_time", "last_sync_time", "sync_status", "local_transactions")},
        ),
        ("Timestamps", {"fields": ("opened_at", "closed_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("cashier", "seller")


@admin.register(POSSale)
class POSSaleAdmin(admin.ModelAdmin):
    list_display = [
        "sale_number",
        "session",
        "cashier",
        "customer_name",
        "total_amount",
        "status",
        "payment_method",
        "created_at",
    ]
    list_filter = ["status", "payment_method", "payment_status", "is_offline_sale", "sync_status", "created_at"]
    search_fields = ["sale_number", "customer_name", "customer_phone", "cashier__username"]
    readonly_fields = ["sale_number", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Sale Information", {"fields": ("sale_number", "session", "cashier", "seller", "status", "payment_status")}),
        ("Customer Information", {"fields": ("customer_name", "customer_phone", "customer_email")}),
        (
            "Financial Details",
            {"fields": ("subtotal", "tax_amount", "tax_rate", "discount_amount", "applied_discounts", "total_amount")},
        ),
        ("Payment Information", {"fields": ("payment_method", "change_amount")}),
        ("Offline Functionality", {"fields": ("is_offline_sale", "offline_transaction_id", "sync_status")}),
        ("Additional Information", {"fields": ("notes", "receipt_number")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("session", "cashier", "seller", "tax_rate")


@admin.register(POSSaleItem)
class POSSaleItemAdmin(admin.ModelAdmin):
    list_display = ["sale", "product", "quantity", "unit_price", "total_price", "item_discount", "item_tax"]
    list_filter = ["sale__created_at"]
    search_fields = ["sale__sale_number", "product__name", "product__sku"]
    ordering = ["-sale__created_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("sale", "product")


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ["receipt_number", "sale", "receipt_type", "generated_at"]
    list_filter = ["receipt_type", "generated_at"]
    search_fields = ["receipt_number", "sale__sale_number"]
    ordering = ["-generated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("sale")


@admin.register(OfflineTransaction)
class OfflineTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "local_transaction_id",
        "session",
        "transaction_type",
        "customer_name",
        "total_amount",
        "sync_status",
        "created_offline_at",
    ]
    list_filter = ["transaction_type", "sync_status", "payment_method", "created_offline_at"]
    search_fields = ["local_transaction_id", "customer_name", "customer_phone", "session__session_id"]
    readonly_fields = ["id", "created_offline_at"]
    ordering = ["-created_offline_at"]

    fieldsets = (
        ("Transaction Information", {"fields": ("id", "session", "local_transaction_id", "transaction_type")}),
        ("Customer Information", {"fields": ("customer_name", "customer_phone", "customer_email")}),
        ("Sale Details", {"fields": ("items_data", "payment_method", "payment_status")}),
        ("Financial Information", {"fields": ("subtotal", "tax_amount", "discount_amount", "total_amount")}),
        ("Sync Status", {"fields": ("sync_status", "sync_attempts", "last_sync_attempt", "sync_error")}),
        ("Metadata", {"fields": ("device_info", "app_version", "created_offline_at")}),
    )

    actions = ["mark_for_sync", "retry_failed_syncs"]

    def mark_for_sync(self, request, queryset):
        updated = queryset.update(sync_status="pending")
        self.message_user(request, f"{updated} transactions marked for sync.")

    mark_for_sync.short_description = "Mark selected transactions for sync"

    def retry_failed_syncs(self, request, queryset):
        failed_transactions = queryset.filter(sync_status="failed")
        updated = failed_transactions.update(sync_status="pending", sync_error="")
        self.message_user(request, f"{updated} failed transactions marked for retry.")

    retry_failed_syncs.short_description = "Retry failed syncs"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("session")

    def has_add_permission(self, request):
        # Offline transactions are created automatically by the system
        return False

    def has_change_permission(self, request, obj=None):
        # Allow editing sync status and error messages
        return True

    def has_delete_permission(self, request, obj=None):
        # Allow deletion of synced transactions
        if obj and obj.sync_status == "synced":
            return True
        return False

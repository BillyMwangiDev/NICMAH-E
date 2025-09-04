from django.contrib import admin
from .models import (
    StockMovement,
    StockAlert,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    InventoryTransaction,
    NotificationPreference,
)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("movement_id", "product", "movement_type", "quantity", "new_stock", "user", "created_at")
    list_filter = ("movement_type", "created_at", "product__category")
    search_fields = ("movement_id", "product__name")
    readonly_fields = ("movement_id", "previous_stock", "new_stock", "created_at")
    date_hierarchy = "created_at"


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = (
        "alert_id",
        "product",
        "alert_type",
        "status",
        "priority",
        "current_value",
        "threshold_value",
        "created_at",
    )
    list_filter = ("alert_type", "status", "priority", "created_at", "product__category")
    search_fields = ("alert_id", "product__name", "message")
    readonly_fields = ("alert_id", "created_at", "updated_at")
    date_hierarchy = "created_at"

    actions = ["acknowledge_alerts", "resolve_alerts", "dismiss_alerts"]

    def acknowledge_alerts(self, request, queryset):
        """Acknowledge selected alerts."""
        updated = queryset.update(status="acknowledged")
        self.message_user(request, f"{updated} alerts have been acknowledged.")

    acknowledge_alerts.short_description = "Acknowledge selected alerts"

    def resolve_alerts(self, request, queryset):
        """Resolve selected alerts."""
        updated = queryset.update(status="resolved")
        self.message_user(request, f"{updated} alerts have been resolved.")

    resolve_alerts.short_description = "Resolve selected alerts"

    def dismiss_alerts(self, request, queryset):
        """Dismiss selected alerts."""
        updated = queryset.update(status="dismissed")
        self.message_user(request, f"{updated} alerts have been dismissed.")

    dismiss_alerts.short_description = "Dismiss selected alerts"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "low_stock_alerts",
        "out_of_stock_alerts",
        "email_notifications",
        "in_app_notifications",
        "notification_frequency",
    )
    list_filter = (
        "low_stock_alerts",
        "out_of_stock_alerts",
        "email_notifications",
        "in_app_notifications",
        "notification_frequency",
    )
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("User", {"fields": ("user",)}),
        (
            "Alert Types",
            {
                "fields": (
                    "low_stock_alerts",
                    "out_of_stock_alerts",
                    "expiring_soon_alerts",
                    "overstock_alerts",
                    "slow_moving_alerts",
                )
            },
        ),
        ("Notification Methods", {"fields": ("email_notifications", "sms_notifications", "in_app_notifications")}),
        ("Settings", {"fields": ("notification_frequency", "quiet_hours_start", "quiet_hours_end")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "supplier", "status", "total_amount", "order_date")
    list_filter = ("status", "order_date")
    search_fields = ("po_number", "supplier__name")
    inlines = [PurchaseOrderItemInline]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_person", "phone", "email", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "contact_person", "phone", "email")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "product", "transaction_type", "quantity", "total_cost", "created_at")
    list_filter = ("transaction_type", "created_at")
    search_fields = ("transaction_id", "product__name")

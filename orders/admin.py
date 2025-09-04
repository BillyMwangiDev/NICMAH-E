from django.contrib import admin
from .models import Cart, CartItem, Order, OrderItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'item_count', 'total_amount', 'created_at', 'expires_at']
    list_filter = ['created_at', 'expires_at']
    search_fields = ['user__username', 'user__email', 'session_key']
    readonly_fields = ['created_at', 'updated_at']
    
    def item_count(self, obj):
        return obj.item_count
    item_count.short_description = 'Items'
    
    def total_amount(self, obj):
        return f"KSh {obj.total_amount}"
    total_amount.short_description = 'Total'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'product', 'quantity', 'unit_price', 'total_price', 'added_at']
    list_filter = ['added_at']
    search_fields = ['product__name', 'cart__user__username']
    readonly_fields = ['added_at']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'customer_name', 'status', 'total_amount', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order_number', 'customer__username', 'customer_name', 'customer_email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    list_editable = ['status']
    
    def total_amount(self, obj):
        return f"KSh {obj.total_amount}"
    total_amount.short_description = 'Total'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product_name', 'quantity', 'unit_price', 'total_price']
    list_filter = ['order__status']
    search_fields = ['product_name', 'order__order_number']

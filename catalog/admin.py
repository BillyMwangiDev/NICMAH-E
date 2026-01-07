from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Category, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "is_admin_only", "product_count", "created_at")
    list_filter = ("is_active", "is_admin_only", "created_at")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "is_admin_only")

    def product_count(self, obj):
        """Display product count with link to filtered products."""
        count = obj.products.count()
        if count > 0:
            url = f"{reverse('admin:catalog_product_changelist')}?category__id__exact={obj.id}"
            return format_html('<a href="{}">{}</a>', url, count)
        return count

    product_count.short_description = "Products"

    # actions method removed to fix admin issues

    def activate_categories(self, request, queryset):
        """Mark selected categories as active."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} categories were successfully marked as active.")

    activate_categories.short_description = "Mark selected categories as active"

    def deactivate_categories(self, request, queryset):
        """Mark selected categories as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} categories were successfully marked as inactive.")

    deactivate_categories.short_description = "Mark selected categories as inactive"


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "alt_text", "order", "is_active")
    readonly_fields = ("created_at",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock_quantity", "stock_status", "is_active", "is_featured", "has_images", "image_actions")
    list_filter = ("is_active", "is_featured", "category", "stock_quantity", "created_at")
    search_fields = ("name", "description", "sku", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]
    list_editable = ("is_active", "is_featured", "price")
    readonly_fields = ("created_at", "updated_at")
    
    change_list_template = "admin/catalog/product/change_list.html"

    fieldsets = (
        ("Basic Information", {"fields": ("name", "slug", "description", "category", "sku")}),
        ("Pricing & Stock", {"fields": ("price", "stock_quantity", "min_stock_level", "is_active", "is_featured")}),
        ("Product Details", {"fields": ("weight", "dimensions", "package_size"), "classes": ("collapse",)}),
        ("Images", {"fields": ("main_image",), "classes": ("collapse",)}),
        ("SEO & Marketing", {"fields": ("meta_title", "meta_description"), "classes": ("collapse",)}),
    )

    def stock_status(self, obj):
        """Display stock status with color coding."""
        if obj.stock_quantity <= 0:
            return format_html('<span style="color: red;">Out of Stock</span>')
        elif obj.is_low_stock:
            return format_html('<span style="color: orange;">Low Stock</span>')
        else:
            return format_html('<span style="color: green;">In Stock</span>')

    stock_status.short_description = "Stock Status"

    def has_images(self, obj):
        """Check if product has images."""
        has_main = bool(obj.main_image)
        has_additional = obj.images.filter(is_active=True).exists()
        if has_main or has_additional:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    
    has_images.short_description = "Images"

    def image_actions(self, obj):
        """Display image management actions."""
        if obj.has_images:
            return format_html(
                '<a href="{}" class="button" style="background: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px;">Manage Images</a>',
                reverse('admin:catalog_product_change', args=[obj.pk])
            )
        else:
            return format_html(
                '<a href="{}" class="button" style="background: #007cba; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px; font-size: 12px;">Add Images</a>',
                reverse('admin:catalog_product_change', args=[obj.pk])
            )
    
    image_actions.short_description = "Image Actions"

    actions = ["make_active", "make_inactive", "mark_as_featured", "mark_as_not_featured", "duplicate_products"]

    def duplicate_products(self, request, queryset):
        """Duplicate selected products."""
        duplicated_count = 0
        for product in queryset:
            product.pk = None
            product.name = f"{product.name} (Copy)"
            product.sku = f"{product.sku}_COPY"
            product.is_active = False
            product.save()
            duplicated_count += 1

        self.message_user(request, f"{duplicated_count} products were successfully duplicated.")

    duplicate_products.short_description = "Duplicate selected products"

    def make_active(self, request, queryset):
        """Mark selected products as active."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} products were successfully marked as active.")

    make_active.short_description = "Mark selected products as active"

    def make_inactive(self, request, queryset):
        """Mark selected products as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} products were successfully marked as inactive.")

    make_inactive.short_description = "Mark selected products as inactive"

    def mark_as_featured(self, request, queryset):
        """Mark selected products as featured."""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"{updated} products were successfully marked as featured.")

    mark_as_featured.short_description = "Mark selected products as featured"

    def mark_as_not_featured(self, request, queryset):
        """Mark selected products as not featured."""
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"{updated} products were successfully marked as not featured.")

    mark_as_not_featured.short_description = "Mark selected products as not featured"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "image_preview", "alt_text", "order", "is_active", "created_at")
    list_filter = ("is_active", "created_at", "product__category")
    search_fields = ("product__name", "alt_text")
    list_editable = ("order", "is_active")
    readonly_fields = ("created_at", "image_preview")
    
    def image_preview(self, obj):
        """Display image preview in admin."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.image.url
            )
        return "No image"
    
    image_preview.short_description = "Preview"

"""
Admin configuration for users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, UserProfile, SellerProfile


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile."""

    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = (
        "bio",
        "website",
        "profile_picture",
        "facebook",
        "twitter",
        "linkedin",
        "newsletter_subscription",
        "marketing_emails",
    )


class SellerProfileInline(admin.StackedInline):
    """Inline admin for SellerProfile."""

    model = SellerProfile
    can_delete = False
    verbose_name_plural = "Seller Profile"
    fields = ("specialization", "experience_years", "certifications", "working_hours", "is_available")


class CustomUserAdmin(UserAdmin):
    """Admin configuration for CustomUser model."""

    model = CustomUser
    list_display = ("email", "username", "first_name", "last_name", "role", "is_seller", "is_active", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_seller", "is_active_seller", "date_joined")
    search_fields = ("email", "username", "first_name", "last_name", "seller_code")
    ordering = ("-date_joined",)
    inlines = [UserProfileInline, SellerProfileInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {"fields": ("username", "first_name", "last_name", "phone_number", "address", "date_of_birth")},
        ),
        (
            _("Role & Permissions"),
            {
                "fields": ("role", "is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        (
            _("Seller Information"),
            {"fields": ("is_seller", "seller_code", "commission_rate", "is_active_seller"), "classes": ("collapse",)},
        ),
        (
            _("Business Info"),
            {"fields": ("business_name", "business_address", "business_phone"), "classes": ("collapse",)},
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "role",
                    "is_seller",
                ),
            },
        ),
    )

    # actions method removed to fix admin issues

    def get_queryset(self, request):
        """Filter users based on admin permissions."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superusers can only see customers and sellers, not managers or admins
        return qs.exclude(role__in=["manager", "admin"])


class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""

    list_display = ("user", "newsletter_subscription", "marketing_emails", "created_at")
    list_filter = ("newsletter_subscription", "marketing_emails", "created_at")
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("user",)}),
        (_("Profile Information"), {"fields": ("bio", "website", "profile_picture")}),
        (_("Social Media"), {"fields": ("facebook", "twitter", "linkedin"), "classes": ("collapse",)}),
        (_("Preferences"), {"fields": ("newsletter_subscription", "marketing_emails")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


class SellerProfileAdmin(admin.ModelAdmin):
    """Admin configuration for SellerProfile model."""

    list_display = ("user", "specialization", "total_sales", "total_orders", "average_rating", "is_available")
    list_filter = ("is_available", "experience_years", "created_at")
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name", "specialization")
    readonly_fields = ("total_sales", "total_orders", "average_rating", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("user",)}),
        (_("Professional Information"), {"fields": ("specialization", "experience_years", "certifications")}),
        (
            _("Performance Metrics"),
            {"fields": ("total_sales", "total_orders", "average_rating"), "classes": ("collapse",)},
        ),
        (_("Working Information"), {"fields": ("working_hours", "is_available")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    # actions method removed to fix admin issues

    def get_queryset(self, request):
        """Filter sellers based on admin permissions."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Non-superusers can only see sellers, not managers or admins
        return qs.filter(user__role="seller")


# Register models - Commented out to use custom admin site
# admin.site.register(CustomUser, CustomUserAdmin)
# admin.site.register(UserProfile, UserProfileAdmin)
# admin.site.register(SellerProfile, SellerProfileAdmin)

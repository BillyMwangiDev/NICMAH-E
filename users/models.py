"""
User models for NICMAH application.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Custom user model with extended fields."""

    class UserRole(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        SELLER = "seller", _("Seller")
        MANAGER = "manager", _("Manager")
        ADMIN = "admin", _("Admin")

    # Basic fields
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)

    # Role and permissions
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.CUSTOMER)

    # Contact information
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    # Business information (for sellers and managers)
    business_name = models.CharField(max_length=100, blank=True)
    business_address = models.TextField(blank=True)
    business_phone = models.CharField(max_length=15, blank=True)

    # Seller specific fields
    is_seller = models.BooleanField(default=False)
    seller_code = models.CharField(max_length=10, unique=True, blank=True, null=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_active_seller = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Override default fields
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = "%s %s" % (self.first_name, self.last_name)
        return full_name.strip()

    def get_role_display(self):
        """Return the human-readable role name."""
        return dict(self.UserRole.choices)[self.role]

    def is_staff_or_higher(self):
        """Check if user is staff, seller, manager, or admin."""
        return self.is_staff or self.role in [self.UserRole.SELLER, self.UserRole.MANAGER, self.UserRole.ADMIN]

    def can_access_pos(self):
        """Check if user can access POS system."""
        return self.role in [self.UserRole.SELLER, self.UserRole.MANAGER, self.UserRole.ADMIN]

    def can_access_analytics(self):
        """Check if user can access analytics."""
        return self.role in [self.UserRole.MANAGER, self.UserRole.ADMIN]

    def can_manage_users(self):
        """Check if user can manage other users."""
        return self.role == self.UserRole.ADMIN

    def save(self, *args, **kwargs):
        """Override save to generate seller code if needed."""
        if self.role == self.UserRole.SELLER and not self.seller_code:
            self.seller_code = self._generate_seller_code()
        super().save(*args, **kwargs)

    def _generate_seller_code(self):
        """Generate unique seller code."""
        import random
        import string

        while True:
            # Generate 6-character alphanumeric code
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not CustomUser.objects.filter(seller_code=code).exists():
                return code


class UserProfile(models.Model):
    """Extended user profile information."""

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="userprofile")

    # Profile information
    bio = models.TextField(blank=True)
    website = models.URLField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)

    # Social media
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    # Preferences
    newsletter_subscription = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")

    def __str__(self):
        return f"{self.user.username}'s Profile"


class SellerProfile(models.Model):
    """Extended seller profile information."""

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="sellerprofile")

    # Seller specific information
    specialization = models.CharField(max_length=100, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    certifications = models.TextField(blank=True)

    # Performance metrics
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_orders = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)

    # Working hours
    working_hours = models.TextField(blank=True)
    is_available = models.BooleanField(default=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Seller Profile")
        verbose_name_plural = _("Seller Profiles")

    def __str__(self):
        return f"{self.user.username}'s Seller Profile"

    def get_commission_earned(self):
        """Calculate total commission earned."""
        return (self.total_sales * self.user.commission_rate) / 100

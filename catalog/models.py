"""
Product catalog models for Nichmah Agrovet application.
"""

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MinLengthValidator


class Category(models.Model):
    """
    Product category model.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:category_detail", kwargs={"slug": self.slug})

    @property
    def product_count(self):
        return self.products.filter(is_active=True).count()


class Product(models.Model):
    """
    Product model for the catalog.
    """

    # Basic information
    name = models.CharField(max_length=200, validators=[MinLengthValidator(3)])
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(validators=[MinLengthValidator(10)])
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")

    # Pricing and stock
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock_quantity = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=5)

    # Product details
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    weight = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True, help_text="Weight in kg")
    dimensions = models.CharField(max_length=100, blank=True, help_text="L x W x H in cm")
    package_size = models.CharField(max_length=50, blank=True, help_text="e.g. 100 ml, 180 ml, 1 L, 500 g")

    # Images
    main_image = models.ImageField(upload_to="products/", blank=True, null=True)
    additional_images = models.JSONField(default=list, blank=True)

    # Status and visibility
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    # SEO and metadata
    meta_title = models.CharField(max_length=60, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "product"
        verbose_name_plural = "products"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["is_featured"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    @property
    def is_low_stock(self):
        """Check if product stock is below minimum level."""
        return self.stock_quantity <= self.min_stock_level

    @property
    def stock_status(self):
        """Get human-readable stock status."""
        if self.stock_quantity == 0:
            return "Out of Stock"
        elif self.is_low_stock:
            return "Low Stock"
        else:
            return "In Stock"

    @property
    def formatted_price(self):
        """Format price with currency symbol."""
        return f"KSh {self.price:.2f}"

    def update_stock(self, quantity_change):
        """
        Update stock quantity (positive for addition, negative for reduction).
        Returns True if successful, False if insufficient stock.
        """
        new_quantity = self.stock_quantity + quantity_change
        if new_quantity < 0:
            return False

        self.stock_quantity = new_quantity
        self.save()
        return True

    @property
    def primary_image(self):
        """Get the primary image (main_image or first additional image)."""
        if self.main_image:
            return self.main_image
        first_additional = self.images.filter(is_active=True).first()
        return first_additional.image if first_additional else None

    @property
    def all_images(self):
        """Get all active images for the product."""
        images = []
        if self.main_image:
            images.append(self.main_image)
        additional_images = self.images.filter(is_active=True).order_by('order')
        images.extend([img.image for img in additional_images])
        return images

    @property
    def has_images(self):
        """Check if product has any images."""
        return bool(self.main_image) or self.images.filter(is_active=True).exists()


class ProductImage(models.Model):
    """
    Additional product images.
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/additional/")
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "created_at"]
        verbose_name = "product image"
        verbose_name_plural = "product images"

    def __str__(self):
        return f"{self.product.name} - Image {self.order}"

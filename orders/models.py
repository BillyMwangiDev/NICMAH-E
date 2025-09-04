from django.db import models
from django.conf import settings
from django.utils import timezone
from catalog.models import Product


class Cart(models.Model):
    """Shopping cart for users"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Cart"
        verbose_name_plural = "Carts"

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart {self.session_key}"

    @property
    def total_amount(self):
        """Calculate total amount of cart"""
        return sum(item.total_price for item in self.items.all())

    @property
    def item_count(self):
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    def is_expired(self):
        """Check if cart has expired"""
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.expires_at or self.expires_at == timezone.now():
            # Set expiration to 30 days from now
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        super().save(*args, **kwargs)


class CartItem(models.Model):
    """Individual items in a cart"""
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cart Item"
        verbose_name_plural = "Cart Items"
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.cart}"

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.quantity * self.unit_price


class Order(models.Model):
    """Customer order"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField()
    shipping_address = models.TextField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.order_number} - {self.customer_name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number
            last_order = Order.objects.order_by('-id').first()
            if last_order:
                last_number = int(last_order.order_number[3:])  # Remove 'ORD' prefix
                self.order_number = f"ORD{last_number + 1:06d}"
            else:
                self.order_number = "ORD000001"
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)  # Store product name at time of order
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    def __str__(self):
        return f"{self.quantity}x {self.product_name} in Order {self.order.order_number}"

    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

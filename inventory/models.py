"""
Inventory management models for Nichmah Agrovet application.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.validators import MinValueValidator
from catalog.models import Product
from decimal import Decimal
import uuid
import random
import string
from django.utils import timezone

User = get_user_model()


class StockMovement(models.Model):
    """
    Track all stock movements (additions, reductions, adjustments).
    """

    class MovementType(models.TextChoices):
        PURCHASE = "purchase", "Purchase"
        SALE = "sale", "Sale"
        ADJUSTMENT = "adjustment", "Adjustment"
        TRANSFER = "transfer", "Transfer"
        RETURN = "return", "Return"
        DAMAGED = "damaged", "Damaged"
        EXPIRED = "expired", "Expired"

    # Movement identification
    movement_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_movements")

    # Movement details
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.IntegerField()  # Positive for additions, negative for reductions
    previous_stock = models.PositiveIntegerField()
    new_stock = models.PositiveIntegerField()

    # Reference information
    reference_number = models.CharField(max_length=50, blank=True)  # Order number, sale number, etc.
    reference_type = models.CharField(max_length=50, blank=True)  # Order, Sale, Adjustment, etc.

    # User and notes
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_movements")
    notes = models.TextField(blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "stock movement"
        verbose_name_plural = "stock movements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["movement_id"]),
            models.Index(fields=["product"]),
            models.Index(fields=["movement_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        movement_sign = "+" if self.quantity > 0 else ""
        return f"{movement_sign}{self.quantity} {self.product.name} ({self.movement_type})"

    def save(self, *args, **kwargs):
        if not self.movement_id:
            self.movement_id = str(uuid.uuid4())
        super().save(*args, **kwargs)


class StockAlert(models.Model):
    """
    Stock alerts for low stock, out of stock, and other inventory issues.
    """

    class AlertType(models.TextChoices):
        LOW_STOCK = "low_stock", "Low Stock"
        OUT_OF_STOCK = "out_of_stock", "Out of Stock"
        OVERSTOCK = "overstock", "Overstock"
        EXPIRING_SOON = "expiring_soon", "Expiring Soon"
        EXPIRED = "expired", "Expired"
        DAMAGED = "damaged", "Damaged"

    class AlertStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    # Alert identification
    alert_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_alerts")

    # Alert details
    alert_type = models.CharField(max_length=20, choices=AlertType.choices)
    status = models.CharField(max_length=20, choices=AlertStatus.choices, default=AlertStatus.ACTIVE)

    # Alert thresholds and values
    threshold_value = models.PositiveIntegerField(blank=True, null=True)
    current_value = models.PositiveIntegerField()

    # Alert message
    message = models.TextField()
    priority = models.CharField(
        max_length=20,
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )

    # User actions
    acknowledged_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="acknowledged_alerts"
    )
    acknowledged_at = models.DateTimeField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="resolved_alerts"
    )
    resolved_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "stock alert"
        verbose_name_plural = "stock alerts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["alert_id"]),
            models.Index(fields=["product"]),
            models.Index(fields=["alert_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.alert_type} Alert for {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.alert_id:
            self.alert_id = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def acknowledge(self, user):
        """Acknowledge the alert."""
        if self.status == self.AlertStatus.ACTIVE:
            self.status = self.AlertStatus.ACKNOWLEDGED
            self.acknowledged_by = user
            self.acknowledged_at = models.timezone.now()
            self.save()

    def resolve(self, user):
        """Resolve the alert."""
        if self.status in [self.AlertStatus.ACTIVE, self.AlertStatus.ACKNOWLEDGED]:
            self.status = self.AlertStatus.RESOLVED
            self.resolved_by = user
            self.resolved_at = models.timezone.now()
            self.save()

    def dismiss(self, user):
        """Dismiss the alert."""
        if self.status == self.AlertStatus.ACTIVE:
            self.status = self.AlertStatus.DISMISSED
            self.acknowledged_by = user
            self.acknowledged_at = models.timezone.now()
            self.save()

    @property
    def is_active(self):
        """Check if alert is active."""
        return self.status == self.AlertStatus.ACTIVE

    @property
    def days_since_created(self):
        """Calculate days since alert was created."""
        from django.utils import timezone

        return (timezone.now() - self.created_at).days


class InventoryTransaction(models.Model):
    """
    Detailed inventory transactions for audit trail.
    """

    class TransactionType(models.TextChoices):
        IN = "in", "Stock In"
        OUT = "out", "Stock Out"
        ADJUST = "adjust", "Adjustment"
        TRANSFER = "transfer", "Transfer"
        COUNT = "count", "Stock Count"

    # Transaction identification
    transaction_id = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="inventory_transactions")

    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity = models.IntegerField()  # Positive for additions, negative for reductions
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.00)])

    # Stock levels
    previous_stock = models.PositiveIntegerField()
    new_stock = models.PositiveIntegerField()

    # Reference information
    reference_number = models.CharField(max_length=50, blank=True)
    reference_type = models.CharField(max_length=50, blank=True)

    # User and location
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_transactions"
    )
    location = models.CharField(max_length=100, blank=True)

    # Notes and metadata
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "inventory transaction"
        verbose_name_plural = "inventory transactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction_id"]),
            models.Index(fields=["product"]),
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.transaction_type} - {self.quantity} {self.product.name}"

    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = str(uuid.uuid4())
        if not self.total_cost:
            self.total_cost = self.unit_cost * abs(self.quantity)
        super().save(*args, **kwargs)


class Supplier(models.Model):
    """
    Supplier information for inventory management.
    """

    name = models.CharField(max_length=200, unique=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Business information
    tax_id = models.CharField(max_length=50, blank=True)
    payment_terms = models.CharField(max_length=100, blank=True)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Status
    is_active = models.BooleanField(default=True)
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "supplier"
        verbose_name_plural = "suppliers"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("inventory:supplier_detail", kwargs={"pk": self.pk})


class PurchaseOrder(models.Model):
    """
    Purchase orders for inventory replenishment.
    """

    class OrderStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent to Supplier"
        CONFIRMED = "confirmed", "Confirmed by Supplier"
        PARTIAL = "partial", "Partially Received"
        RECEIVED = "received", "Fully Received"
        CANCELLED = "cancelled", "Cancelled"

    # Order identification
    po_number = models.CharField(max_length=20, unique=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="purchase_orders")

    # Order details
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.DRAFT)
    order_date = models.DateField()
    expected_delivery = models.DateField(blank=True, null=True)

    # Financial details
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    # Notes and metadata
    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)

    # User and timestamps
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_purchase_orders")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "purchase order"
        verbose_name_plural = "purchase orders"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PO {self.po_number} - {self.supplier.name}"

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = self.generate_po_number()
        super().save(*args, **kwargs)

    def generate_po_number(self):
        """Generate unique purchase order number."""
        import random
        import string

        timestamp = self.order_date.strftime("%Y%m%d") if self.order_date else "00000000"
        random_chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"PO-{timestamp}-{random_chars}"

    def calculate_totals(self):
        """Calculate order totals based on items."""
        self.subtotal = sum(item.total_cost for item in self.items.all())
        self.total_amount = self.subtotal + self.tax_amount + self.shipping_amount
        self.save()

    @property
    def item_count(self):
        """Get total number of items in the order."""
        return sum(item.quantity for item in self.items.all())


class PurchaseOrderItem(models.Model):
    """
    Individual items within a purchase order.
    """

    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="purchase_order_items")

    # Item details
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    received_quantity = models.PositiveIntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "purchase order item"
        verbose_name_plural = "purchase order items"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.quantity}x {self.product.name} in PO {self.purchase_order.po_number}"

    @property
    def total_cost(self):
        """Calculate total cost for this item."""
        return self.unit_cost * self.quantity

    @property
    def remaining_quantity(self):
        """Calculate remaining quantity to be received."""
        return self.quantity - self.received_quantity

    @property
    def is_fully_received(self):
        """Check if item is fully received."""
        return self.received_quantity >= self.quantity


class NotificationPreference(models.Model):
    """
    User preferences for stock notifications.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")

    # Notification types
    low_stock_alerts = models.BooleanField(default=True)
    out_of_stock_alerts = models.BooleanField(default=True)
    expiring_soon_alerts = models.BooleanField(default=True)
    overstock_alerts = models.BooleanField(default=False)
    slow_moving_alerts = models.BooleanField(default=False)

    # Notification methods
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    in_app_notifications = models.BooleanField(default=True)

    # Frequency settings
    notification_frequency = models.CharField(
        max_length=20,
        choices=[("immediate", "Immediate"), ("hourly", "Hourly"), ("daily", "Daily"), ("weekly", "Weekly")],
        default="immediate",
    )

    # Quiet hours (no notifications during these hours)
    quiet_hours_start = models.TimeField(blank=True, null=True)
    quiet_hours_end = models.TimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "notification preference"
        verbose_name_plural = "notification preferences"

    def __str__(self):
        return f"Notification Preferences for {self.user.username}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def is_quiet_hours(self):
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False

        from django.utils import timezone

        now = timezone.now().time()

        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:  # Crosses midnight
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class StockAlertManager:
    """
    Manager for StockAlert model to handle alert generation and management.
    """

    def __init__(self, product, current_stock, threshold_value):
        self.product = product
        self.current_stock = current_stock
        self.threshold_value = threshold_value

    def generate_low_stock_alert(self, user):
        """Generate a low stock alert."""
        if self.current_stock < self.threshold_value:
            alert = StockAlert.objects.create(
                product=self.product,
                alert_type=StockAlert.AlertType.LOW_STOCK,
                current_value=self.current_stock,
                message=f"Low stock alert for {self.product.name}. Current stock: {self.current_stock}",
                priority="high",
            )
            alert.acknowledge(user)
            return alert
        return None

    def generate_out_of_stock_alert(self, user):
        """Generate an out of stock alert."""
        if self.current_stock == 0:
            alert = StockAlert.objects.create(
                product=self.product,
                alert_type=StockAlert.AlertType.OUT_OF_STOCK,
                current_value=self.current_stock,
                message=f"Out of stock alert for {self.product.name}. Current stock: {self.current_stock}",
                priority="critical",
            )
            alert.acknowledge(user)
            return alert
        return None

    def generate_overstock_alert(self, user):
        """Generate an overstock alert."""
        if self.current_stock > self.threshold_value:
            alert = StockAlert.objects.create(
                product=self.product,
                alert_type=StockAlert.AlertType.OVERSTOCK,
                current_value=self.current_stock,
                message=f"Overstock alert for {self.product.name}. Current stock: {self.current_stock}",
                priority="medium",
            )
            alert.acknowledge(user)
            return alert
        return None

    def generate_expiring_soon_alert(self, user):
        """Generate an expiring soon alert."""
        # This method would typically check product expiration date
        # For now, it's a placeholder.
        # If a product has an expiration date, you would compare it to the current date.
        # If the product is expiring soon, generate an alert.
        # Example:
        # if self.product.expiration_date and self.product.expiration_date < timezone.now().date():
        #     alert = StockAlert.objects.create(
        #         product=self.product,
        #         alert_type=StockAlert.AlertType.EXPIRING_SOON,
        #         current_value=self.current_stock,
        #         message=f"Expiring soon alert for {self.product.name}. Current stock: {self.current_stock}",
        #         priority='medium'
        #     )
        #     alert.acknowledge(user)
        #     return alert
        return None

    def generate_damaged_alert(self, user):
        """Generate a damaged alert."""
        # This method would typically check product damage status
        # For now, it's a placeholder.
        # If a product is damaged, generate an alert.
        # Example:
        # if self.product.is_damaged:
        #     alert = StockAlert.objects.create(
        #         product=self.product,
        #         alert_type=StockAlert.AlertType.DAMAGED,
        #         current_value=self.current_stock,
        #         message=f"Damaged alert for {self.product.name}. Current stock: {self.current_stock}",
        #         priority='critical'
        #     )
        #     alert.acknowledge(user)
        #     return alert
        return None

# Document Models
class DocumentTemplate(models.Model):
    """Template for different types of documents."""
    DOCUMENT_TYPES = [
        ('receipt', 'Receipt'),
        ('quotation', 'Quotation'),
        ('invoice', 'Invoice'),
        ('purchase_order', 'Purchase Order'),
    ]
    
    name = models.CharField(max_length=100)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    template_html = models.TextField(help_text="HTML template for the document")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_document_type_display()})"


class Document(models.Model):
    """Base document model for all document types."""
    DOCUMENT_STATUS = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    document_number = models.CharField(max_length=50, unique=True)
    document_type = models.CharField(max_length=20, choices=DocumentTemplate.DOCUMENT_TYPES)
    template = models.ForeignKey(DocumentTemplate, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=DOCUMENT_STATUS, default='draft')
    
    # Document details
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Parties involved
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='created_documents')
    customer_name = models.CharField(max_length=200)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_address = models.TextField(blank=True)
    
    # Financial details
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Dates
    issue_date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional fields
    notes = models.TextField(blank=True)
    terms_conditions = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.document_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.document_number:
            self.document_number = self.generate_document_number()
        super().save(*args, **kwargs)
    
    def generate_document_number(self):
        """Generate unique document number."""
        prefix = self.document_type.upper()[:3]
        year = timezone.now().year
        month = timezone.now().month
        day = timezone.now().day
        hour = timezone.now().hour
        minute = timezone.now().minute
        second = timezone.now().second
        
        return f"{prefix}{year}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}"


class DocumentItem(models.Model):
    """Items within a document."""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        if not self.total_price:
            self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

"""
POS (Point of Sale) models for Nicmah Agrovet application.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone
from catalog.models import Product
import random
import string

User = get_user_model()


def generate_session_id():
    """Generate a shorter session ID."""
    timestamp = timezone.now().strftime('%m%d%H')  # Only month, day, hour
    random_char = ''.join(random.choices(string.ascii_uppercase + string.digits, k=1))
    return f"S{timestamp}{random_char}"


class Barcode(models.Model):
    """Barcode model for product identification."""

    barcode = models.CharField(max_length=50, unique=True, help_text="Product barcode (EAN-13, UPC, etc.)")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="barcodes")
    barcode_type = models.CharField(
        max_length=20,
        choices=[("ean13", "EAN-13"), ("upc", "UPC"), ("code128", "Code 128"), ("qr", "QR Code"), ("custom", "Custom")],
        default="ean13",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Barcode"
        verbose_name_plural = "Barcodes"
        ordering = ["barcode"]

    def __str__(self):
        return f"{self.barcode} - {self.product.name}"


class TaxRate(models.Model):
    """Tax rate configuration for different product categories."""

    name = models.CharField(max_length=50, unique=True)
    rate = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0.00)], help_text="Tax rate as percentage"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Discount(models.Model):
    """Discount and promotion system."""

    name = models.CharField(max_length=100)
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ("percentage", "Percentage"),
            ("fixed_amount", "Fixed Amount"),
            ("buy_one_get_one", "Buy One Get One"),
            ("bulk_discount", "Bulk Discount"),
        ],
        default="percentage",
    )

    # Discount value based on type
    percentage_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        blank=True,
        null=True,
        help_text="Discount percentage (0-100)",
    )
    fixed_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        blank=True,
        null=True,
        help_text="Fixed discount amount",
    )

    # Conditions
    minimum_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        blank=True,
        null=True,
        help_text="Minimum purchase amount to qualify",
    )
    minimum_quantity = models.PositiveIntegerField(blank=True, null=True, help_text="Minimum quantity to qualify")

    # Validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    # Usage limits
    max_uses = models.PositiveIntegerField(
        blank=True, null=True, help_text="Maximum number of times this discount can be used"
    )
    current_uses = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Discount"
        verbose_name_plural = "Discounts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_discount_type_display()})"

    def is_valid(self):
        """Check if discount is currently valid."""
        now = timezone.now()
        return (
            self.is_active
            and self.start_date <= now <= self.end_date
            and (self.max_uses is None or self.current_uses < self.max_uses)
        )

    def calculate_discount(self, subtotal, quantity=1):
        """Calculate discount amount based on type and conditions."""
        if not self.is_valid():
            return Decimal("0.00")

        # Check minimum conditions
        if self.minimum_amount and subtotal < self.minimum_amount:
            return Decimal("0.00")

        if self.minimum_quantity and quantity < self.minimum_quantity:
            return Decimal("0.00")

        # Calculate discount
        if self.discount_type == "percentage" and self.percentage_rate:
            return (subtotal * self.percentage_rate) / 100
        elif self.discount_type == "fixed_amount" and self.fixed_amount:
            return min(self.fixed_amount, subtotal)
        elif self.discount_type == "buy_one_get_one" and quantity >= 2:
            # Buy one get one free - discount the cheaper item
            return subtotal / quantity  # Simplified calculation
        elif self.discount_type == "bulk_discount" and quantity >= (self.minimum_quantity or 1):
            if self.percentage_rate:
                return (subtotal * self.percentage_rate) / 100
            elif self.fixed_amount:
                return self.fixed_amount

        return Decimal("0.00")


class POSSession(models.Model):
    """POS session for tracking cashier activities."""

    session_id = models.CharField(max_length=20, unique=True, default=generate_session_id)
    cashier = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pos_sessions")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_sessions", null=True, blank=True)

    # Session status
    status = models.CharField(
        max_length=20,
        choices=[("open", "Open"), ("closed", "Closed"), ("suspended", "Suspended"), ("offline", "Offline")],
        default="open",
    )

    # Financial tracking
    opening_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    closing_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_transactions = models.PositiveIntegerField(default=0)

    # Enhanced tracking
    total_tax_collected = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_discounts_given = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_card_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_mobile_money_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Timestamps
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Offline functionality fields
    is_offline = models.BooleanField(default=False)
    offline_start_time = models.DateTimeField(null=True, blank=True)
    last_sync_time = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ("synced", "Synced"),
            ("pending", "Pending Sync"),
            ("failed", "Sync Failed"),
            ("offline", "Offline Mode"),
        ],
        default="synced",
    )
    local_transactions = models.JSONField(default=list, blank=True)

    class Meta:
        verbose_name = "POS Session"
        verbose_name_plural = "POS Sessions"
        ordering = ["-opened_at"]

    def __str__(self):
        seller_name = f" - {self.seller.get_full_name()}" if self.seller else ""
        return f"Session {self.session_id} by {self.cashier.get_full_name()}{seller_name}"

    def close_session(self):
        """Close the POS session."""
        self.status = "closed"
        self.closed_at = timezone.now()
        self.save()

    def start_offline_mode(self):
        """Start offline mode for this session"""
        self.is_offline = True
        self.status = "offline"
        self.offline_start_time = timezone.now()
        self.sync_status = "offline"
        self.save()

    def end_offline_mode(self):
        """End offline mode and prepare for sync"""
        self.is_offline = False
        self.status = "open"
        self.sync_status = "pending"
        self.save()

    def add_offline_transaction(self, transaction_data):
        """Add transaction to local storage during offline mode"""
        if self.is_offline:
            transaction_data["local_id"] = str(uuid.uuid4())
            transaction_data["timestamp"] = timezone.now().isoformat()
            self.local_transactions.append(transaction_data)
            self.save()
            return transaction_data["local_id"]
        return None

    def sync_offline_transactions(self):
        """Sync offline transactions when connection is restored"""
        if not self.is_offline and self.local_transactions:
            # Process offline transactions
            for transaction in self.local_transactions:
                # Create actual POSSale records
                self._create_sale_from_offline(transaction)

            # Clear local transactions and update sync status
            self.local_transactions = []
            self.sync_status = "synced"
            self.last_sync_time = timezone.now()
            self.save()

    def _create_sale_from_offline(self, transaction_data):
        """Create a POSSale record from offline transaction data"""
        try:
            # Create the sale record from offline transaction data
            sale = POSSale.objects.create(
                session=self,
                total_amount=Decimal(transaction_data.get("total_amount", "0.00")),
                amount_paid=Decimal(transaction_data.get("amount_paid", "0.00")),
                change_given=Decimal(transaction_data.get("change_given", "0.00")),
                payment_method=transaction_data.get("payment_method", "cash"),
                notes=f"Offline transaction - {transaction_data.get('timestamp', 'Unknown time')}",
                is_offline=True,
            )

            # Create sale items if provided
            items_data = transaction_data.get("items", [])
            for item_data in items_data:
                try:
                    product = Product.objects.get(id=item_data.get("product_id"))
                    POSSaleItem.objects.create(
                        sale=sale,
                        product=product,
                        quantity=int(item_data.get("quantity", 1)),
                        unit_price=Decimal(str(item_data.get("unit_price", "0.00"))),
                        total_price=Decimal(str(item_data.get("total_price", "0.00"))),
                    )
                except Product.DoesNotExist:
                    continue

            return sale
        except Exception as e:
            # Log the error and return None
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error creating sale from offline transaction: {str(e)}")
            return None

    def get_total_commission(self):
        """Calculate total commission for the seller."""
        if self.seller and self.seller.commission_rate:
            return (self.total_sales * self.seller.commission_rate) / 100
        return Decimal("0.00")

    def get_session_summary(self):
        """Get comprehensive session summary."""
        return {
            "session_id": self.session_id,
            "cashier": self.cashier.get_full_name(),
            "seller": self.seller.get_full_name() if self.seller else "None",
            "status": self.status,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "total_sales": self.total_sales,
            "total_transactions": self.total_transactions,
            "total_tax_collected": self.total_tax_collected,
            "total_discounts_given": self.total_discounts_given,
            "payment_breakdown": {
                "cash": self.total_cash_sales,
                "card": self.total_card_sales,
                "mobile_money": self.total_mobile_money_sales,
            },
            "offline_info": {
                "is_offline": self.is_offline,
                "sync_status": self.sync_status,
                "offline_transactions_count": len(self.local_transactions),
                "last_sync_time": self.last_sync_time,
            },
        }


class POSSale(models.Model):
    """Individual POS sale transaction."""

    sale_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    session = models.ForeignKey(POSSession, on_delete=models.CASCADE, related_name="sales", null=True, blank=True)
    cashier = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pos_sales")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_sales", null=True, blank=True)

    # Customer information
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_email = models.EmailField(blank=True)

    # Sale details
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("refunded", "Refunded"),
            ("offline", "Offline"),
        ],
        default="pending",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=[
            ("cash", "Cash"),
            ("card", "Card"),
            ("mobile_money", "Mobile Money"),
            ("bank_transfer", "Bank Transfer"),
            ("offline", "Offline Payment"),
        ],
        default="cash",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("paid", "Paid"), ("failed", "Failed"), ("refunded", "Refunded")],
        default="pending",
    )

    # Financial information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Enhanced fields
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.SET_NULL, null=True, blank=True)
    applied_discounts = models.ManyToManyField(Discount, blank=True, related_name="applied_sales")
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Additional information
    notes = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Offline functionality fields
    is_offline_sale = models.BooleanField(default=False)
    offline_transaction_id = models.CharField(max_length=100, blank=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[("synced", "Synced"), ("pending", "Pending Sync"), ("failed", "Sync Failed")],
        default="synced",
    )

    class Meta:
        verbose_name = "POS Sale"
        verbose_name_plural = "POS Sales"
        ordering = ["-created_at"]

    def __str__(self):
        seller_name = f" - {self.seller.get_full_name()}" if self.seller else ""
        return f"Sale {self.sale_number} by {self.cashier.get_full_name()}{seller_name}"

    def save(self, *args, **kwargs):
        """Override save to calculate totals and update session."""
        if not self.pk:  # New sale
            # Set seller from session if not specified
            if not self.seller and self.session and self.session.seller:
                self.seller = self.session.seller

        # Calculate totals
        self.subtotal = sum(item.total_price for item in self.items.all())

        # Calculate tax
        if self.tax_rate:
            self.tax_amount = (self.subtotal * self.tax_rate.rate) / 100
        else:
            self.tax_amount = Decimal("0.00")

        # Calculate discount
        self.discount_amount = self._calculate_total_discount()

        # Calculate final total
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount

        super().save(*args, **kwargs)

        # Update session totals
        if self.session:
            self._update_session_totals()

    def _calculate_total_discount(self):
        """Calculate total discount from all applied discounts."""
        total_discount = Decimal("0.00")
        for discount in self.applied_discounts.all():
            if discount.is_valid():
                total_discount += discount.calculate_discount(self.subtotal)
        return total_discount

    def _update_session_totals(self):
        """Update session totals with this sale."""
        session = self.session
        session.total_sales += self.total_amount
        session.total_transactions += 1
        session.total_tax_collected += self.tax_amount
        session.total_discounts_given += self.discount_amount

        # Update payment method totals
        if self.payment_method == "cash":
            session.total_cash_sales += self.total_amount
        elif self.payment_method == "card":
            session.total_card_sales += self.total_amount
        elif self.payment_method == "mobile_money":
            session.total_mobile_money_sales += self.total_amount

        session.save()

    def get_commission_amount(self):
        """Calculate commission amount for this sale."""
        if self.seller and self.seller.commission_rate:
            return (self.total_amount * self.seller.commission_rate) / 100
        return Decimal("0.00")

    def apply_discount(self, discount):
        """Apply a discount to this sale."""
        if discount.is_valid():
            self.applied_discounts.add(discount)
            discount.current_uses += 1
            discount.save()
            self.save()  # Recalculate totals
            return True
        return False

    def mark_as_offline(self, local_id=None):
        """Mark this sale as an offline transaction"""
        self.is_offline_sale = True
        self.status = "offline"
        self.sync_status = "pending"
        if local_id:
            self.offline_transaction_id = local_id
        self.save()

    def sync_to_server(self):
        """Sync offline sale to server"""
        if self.is_offline_sale:
            self.sync_status = "synced"
            self.save()
            return True
        return False

    def get_sale_summary(self):
        """Get comprehensive sale summary."""
        return {
            "sale_number": self.sale_number,
            "customer": self.customer_name or "Walk-in Customer",
            "cashier": self.cashier.get_full_name(),
            "seller": self.seller.get_full_name() if self.seller else "None",
            "status": self.status,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "discount_amount": self.discount_amount,
            "total_amount": self.total_amount,
            "change_amount": self.change_amount,
            "created_at": self.created_at,
            "items_count": self.items.count(),
            "offline_info": {
                "is_offline": self.is_offline_sale,
                "sync_status": self.sync_status,
                "offline_id": self.offline_transaction_id,
            },
        }


class POSSaleItem(models.Model):
    """Individual items in a POS sale."""

    sale = models.ForeignKey(POSSale, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Enhanced fields
    item_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    item_tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    applied_discounts = models.ManyToManyField(Discount, blank=True, related_name="applied_items")

    # Additional information
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "POS Sale Item"
        verbose_name_plural = "POS Sale Items"

    def __str__(self):
        return f"{self.quantity}x {self.product.name} - ${self.total_price}"

    def save(self, *args, **kwargs):
        """Override save to calculate total price and update stock."""
        if not self.pk:  # New item
            # Update product stock
            if self.product.stock_quantity >= self.quantity:
                self.product.stock_quantity -= self.quantity
                self.product.save()
            else:
                raise ValueError(f"Insufficient stock for {self.product.name}")

        # Calculate total price
        self.total_price = (self.quantity * self.unit_price) - self.item_discount + self.item_tax

        super().save(*args, **kwargs)

    def apply_item_discount(self, discount):
        """Apply a discount to this specific item."""
        if discount.is_valid():
            self.applied_discounts.add(discount)
            # Calculate item discount
            if discount.discount_type == "percentage" and discount.percentage_rate:
                self.item_discount = (self.quantity * self.unit_price * discount.percentage_rate) / 100
            elif discount.discount_type == "fixed_amount" and discount.fixed_amount:
                self.item_discount = min(discount.fixed_amount, self.quantity * self.unit_price)

            self.save()
            return True
        return False


class Receipt(models.Model):
    """Receipt for POS sales."""

    receipt_number = models.CharField(max_length=50, unique=True)
    sale = models.OneToOneField(POSSale, on_delete=models.CASCADE, related_name="receipt")

    receipt_type = models.CharField(
        max_length=20,
        choices=[("customer", "Customer Receipt"), ("duplicate", "Duplicate Receipt"), ("refund", "Refund Receipt")],
        default="customer",
    )

    # Receipt content
    content = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Receipt"
        verbose_name_plural = "Receipts"
        ordering = ["-generated_at"]

    def __str__(self):
        return f"Receipt {self.receipt_number} for Sale {self.sale.sale_number}"

    def generate_pdf(self):
        """Generate PDF receipt using ReportLab."""
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from io import BytesIO

        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []

        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=16, spaceAfter=30, alignment=1  # Center alignment
        )

        # Header
        story.append(Paragraph("NICMAH AGROVET", title_style))
        story.append(Paragraph("Receipt", styles["Heading2"]))
        story.append(Spacer(1, 20))

        # Sale information
        sale_data = [
            ["Receipt Number:", self.receipt_number],
            ["Sale Number:", self.sale.sale_number],
            ["Date:", self.sale.created_at.strftime("%Y-%m-%d %H:%M")],
            ["Cashier:", self.sale.cashier.get_full_name()],
        ]

        if self.sale.seller:
            sale_data.append(["Seller:", self.sale.seller.get_full_name()])

        sale_table = Table(sale_data, colWidths=[2 * inch, 4 * inch])
        sale_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ]
            )
        )

        story.append(sale_table)
        story.append(Spacer(1, 20))

        # Items table
        items_data = [["Item", "Qty", "Price", "Total"]]
        for item in self.sale.items.all():
            items_data.append([item.product.name, str(item.quantity), f"${item.unit_price}", f"${item.total_price}"])

        items_table = Table(items_data, colWidths=[3 * inch, 1 * inch, 1 * inch, 1 * inch])
        items_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        story.append(items_table)
        story.append(Spacer(1, 20))

        # Totals
        totals_data = [
            ["Subtotal:", f"${self.sale.subtotal}"],
            ["Tax:", f"${self.sale.tax_amount}"],
            ["Discount:", f"${self.sale.discount_amount}"],
            ["Total:", f"${self.sale.total_amount}"],
        ]

        totals_table = Table(totals_data, colWidths=[2 * inch, 1 * inch])
        totals_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        story.append(totals_table)
        story.append(Spacer(1, 30))

        # Footer
        story.append(Paragraph("Thank you for your business!", styles["Normal"]))
        story.append(Paragraph("NICMAH AGROVET - Quality Agricultural Solutions", styles["Normal"]))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer


class OfflineTransaction(models.Model):
    """Model to store offline transactions for later sync."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(POSSession, on_delete=models.CASCADE, related_name="offline_transactions")
    local_transaction_id = models.CharField(max_length=100, unique=True)

    # Transaction data
    transaction_type = models.CharField(
        max_length=20, choices=[("sale", "Sale"), ("refund", "Refund"), ("void", "Void")], default="sale"
    )

    # Customer information
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    customer_email = models.EmailField(blank=True)

    # Sale details
    items_data = models.JSONField(help_text="Stored items data for offline transactions")
    payment_method = models.CharField(max_length=20, default="cash")
    payment_status = models.CharField(max_length=20, default="paid")

    # Financial information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Offline tracking
    created_offline_at = models.DateTimeField(auto_now_add=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending Sync"), ("syncing", "Syncing"), ("synced", "Synced"), ("failed", "Sync Failed")],
        default="pending",
    )
    sync_attempts = models.PositiveIntegerField(default=0)
    last_sync_attempt = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True)

    # Metadata
    device_info = models.JSONField(default=dict, blank=True)
    app_version = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Offline Transaction"
        verbose_name_plural = "Offline Transactions"
        ordering = ["-created_offline_at"]

    def __str__(self):
        return f"Offline {self.transaction_type} - {self.local_transaction_id}"

    def mark_syncing(self):
        """Mark transaction as currently syncing"""
        self.sync_status = "syncing"
        self.last_sync_attempt = timezone.now()
        self.sync_attempts += 1
        self.save()

    def mark_synced(self):
        """Mark transaction as successfully synced"""
        self.sync_status = "synced"
        self.save()

    def mark_sync_failed(self, error_message):
        """Mark transaction as failed to sync"""
        self.sync_status = "failed"
        self.sync_error = error_message
        self.last_sync_attempt = timezone.now()
        self.save()

    def get_transaction_summary(self):
        """Get summary of offline transaction"""
        return {
            "local_id": self.local_transaction_id,
            "type": self.transaction_type,
            "customer": self.customer_name or "Walk-in Customer",
            "total_amount": self.total_amount,
            "payment_method": self.payment_method,
            "created_at": self.created_offline_at,
            "sync_status": self.sync_status,
            "items_count": len(self.items_data) if self.items_data else 0,
        }

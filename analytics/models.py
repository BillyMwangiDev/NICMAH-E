"""
Analytics and reporting models for NICMAH application.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
import json
from catalog.models import Product

User = get_user_model()


class Sales(models.Model):
    """Unified sales tracking for both POS and e-commerce"""
    
    SALE_TYPE_CHOICES = [
        ('pos', 'POS Sale'),
        ('ecommerce', 'E-commerce Sale'),
        ('manual', 'Manual Sale'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('whatsapp', 'WhatsApp'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Basic sale information
    sale_number = models.CharField(max_length=50, unique=True)
    sale_type = models.CharField(max_length=20, choices=SALE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    
    # Customer information
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_address = models.TextField(blank=True)
    
    # Financial information
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    change_given = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Payment information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    # Staff information
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales_cashier')
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales_seller')
    
    # Reference to original sale records
    pos_sale = models.ForeignKey('pos.POSSale', on_delete=models.SET_NULL, null=True, blank=True)
    ecommerce_order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional information
    notes = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Sale {self.sale_number} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.sale_number:
            # Generate sale number
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_suffix = ''.join([str(timezone.now().microsecond)[-3:]])
            self.sale_number = f"SALE{timestamp}{random_suffix}"
        
        # Ensure all financial fields are Decimal
        self.subtotal = Decimal(str(self.subtotal or 0))
        self.tax_amount = Decimal(str(self.tax_amount or 0))
        self.discount_amount = Decimal(str(self.discount_amount or 0))
        
        # Calculate totals if not set or recalculate to ensure accuracy
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        # Validation: Ensure total_amount is not negative
        if self.total_amount < Decimal("0.00"):
            self.total_amount = Decimal("0.00")
        
        if not self.amount_paid:
            self.amount_paid = self.total_amount
        else:
            self.amount_paid = Decimal(str(self.amount_paid))
            
        if self.amount_paid > self.total_amount:
            self.change_given = self.amount_paid - self.total_amount
        else:
            self.change_given = Decimal("0.00")
            
        super().save(*args, **kwargs)


class SalesItem(models.Model):
    """Individual items in a sale"""
    
    sale = models.ForeignKey(Sales, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Reference to original item records
    pos_sale_item = models.ForeignKey('pos.POSSaleItem', on_delete=models.SET_NULL, null=True, blank=True)
    order_item = models.ForeignKey('orders.OrderItem', on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"
        
    def __str__(self):
        return f"{self.quantity}x {self.product.name} in {self.sale.sale_number}"
    
    def save(self, *args, **kwargs):
        # Ensure all values are Decimal for accurate calculations
        self.quantity = int(self.quantity)
        self.unit_price = Decimal(str(self.unit_price))
        
        # Calculate total price
        if not self.total_price:
            self.total_price = Decimal(str(self.quantity)) * self.unit_price
        else:
            # Recalculate to ensure accuracy
            self.total_price = Decimal(str(self.quantity)) * self.unit_price
        
        super().save(*args, **kwargs)


class SalesAnalytics(models.Model):
    """Daily sales analytics summary"""
    
    date = models.DateField(unique=True)
    
    # Sales counts
    total_sales = models.PositiveIntegerField(default=0)
    pos_sales = models.PositiveIntegerField(default=0)
    ecommerce_sales = models.PositiveIntegerField(default=0)
    manual_sales = models.PositiveIntegerField(default=0)
    
    # Financial totals
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    pos_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    ecommerce_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    manual_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Tax and discounts
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_discounts = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Payment methods
    cash_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    card_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    mobile_money_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    bank_transfer_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    whatsapp_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    other_sales = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Top products
    top_products = models.TextField(default='[]', blank=True, help_text="JSON array of top products")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_top_products(self):
        """Get top products as a list."""
        import json
        if not self.top_products:
            return []
        try:
            return json.loads(self.top_products)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_top_products(self, value):
        """Set top products from a list."""
        import json
        if value is None:
            self.top_products = '[]'
        else:
            self.top_products = json.dumps(value)
    
    class Meta:
        verbose_name = "Sales Analytics"
        verbose_name_plural = "Sales Analytics"
        ordering = ['-date']
        
    def __str__(self):
        return f"Sales Analytics for {self.date}"
    
    @classmethod
    def get_or_create_for_date(cls, date):
        """Get or create analytics for a specific date"""
        analytics, created = cls.objects.get_or_create(date=date)
        if created:
            # Calculate analytics for this date
            analytics.calculate_daily_analytics()
        return analytics
    
    def calculate_daily_analytics(self):
        """Calculate daily analytics from sales data"""
        from django.db.models import Sum, Count
        
        # Get sales for this date
        sales = Sales.objects.filter(
            created_at__date=self.date,
            status='completed'
        )
        
        # Calculate totals
        self.total_sales = sales.count()
        self.total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.total_tax = sales.aggregate(total=Sum('tax_amount'))['total'] or Decimal('0.00')
        self.total_discounts = sales.aggregate(total=Sum('discount_amount'))['total'] or Decimal('0.00')
        
        # Calculate by sale type
        pos_sales = sales.filter(sale_type='pos')
        ecommerce_sales = sales.filter(sale_type='ecommerce')
        manual_sales = sales.filter(sale_type='manual')
        
        self.pos_sales = pos_sales.count()
        self.ecommerce_sales = ecommerce_sales.count()
        self.manual_sales = manual_sales.count()
        
        self.pos_revenue = pos_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.ecommerce_revenue = ecommerce_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.manual_revenue = manual_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Calculate by payment method
        self.cash_sales = sales.filter(payment_method='cash').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.card_sales = sales.filter(payment_method='card').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.mobile_money_sales = sales.filter(payment_method='mobile_money').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.bank_transfer_sales = sales.filter(payment_method='bank_transfer').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.whatsapp_sales = sales.filter(payment_method='whatsapp').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        self.other_sales = sales.filter(payment_method='other').aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Calculate top products
        from django.db.models import Sum
        top_products = SalesItem.objects.filter(
            sale__created_at__date=self.date,
            sale__status='completed'
        ).values('product__name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_quantity')[:10]
        
        self.set_top_products(list(top_products))
        
        self.save()

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from .models import Sales, SalesItem
from pos.models import POSSale, POSSaleItem
from orders.models import Order, OrderItem


@receiver(post_save, sender=POSSale)
def create_unified_sale_from_pos(sender, instance, created, **kwargs):
    """Create unified sales record when POS sale is created or status changes to completed"""
    # Check if sale is completed and unified sale doesn't exist yet
    if instance.status == 'completed':
        # Check if unified sale already exists to avoid duplicates
        if not Sales.objects.filter(pos_sale=instance).exists():
            # Calculate amount_paid from total_amount + change_amount
            amount_paid = instance.total_amount + instance.change_amount
            
            # Create unified sale record
            unified_sale = Sales.objects.create(
                sale_type='pos',
                status='completed',
                customer_name=instance.customer_name or 'Walk-in Customer',
                customer_phone=instance.customer_phone or '',
                customer_email=instance.customer_email or '',
                customer_address='',
                subtotal=instance.subtotal,
                tax_amount=instance.tax_amount,
                discount_amount=instance.discount_amount,
                total_amount=instance.total_amount,
                amount_paid=amount_paid,
                change_given=instance.change_amount,
                payment_method=instance.payment_method,
                cashier=instance.cashier,
                seller=instance.seller,
                pos_sale=instance,
                notes=instance.notes,
                receipt_number=instance.receipt_number or ''
            )
            
            # Create unified sale items
            for pos_item in instance.items.all():
                SalesItem.objects.create(
                    sale=unified_sale,
                    product=pos_item.product,
                    quantity=pos_item.quantity,
                    unit_price=pos_item.unit_price,
                    total_price=pos_item.total_price,
                    pos_sale_item=pos_item
                )


@receiver(post_save, sender=Order)
def create_unified_sale_from_ecommerce(sender, instance, created, **kwargs):
    """Create unified sales record when e-commerce order is created or status changes"""
    # Check if order is in a completed status and unified sale doesn't exist yet
    if instance.status in ['confirmed', 'processing', 'shipped', 'delivered']:
        # Check if unified sale already exists to avoid duplicates
        if not Sales.objects.filter(ecommerce_order=instance).exists():
            # Determine payment method from order
            payment_method = 'whatsapp'  # Default for e-commerce orders
            
            # Create unified sale record
            unified_sale = Sales.objects.create(
                sale_type='ecommerce',
                status='completed',
                customer_name=instance.customer_name,
                customer_phone=instance.customer_phone,
                customer_email=instance.customer_email,
                customer_address=instance.shipping_address,
                subtotal=instance.total_amount,  # Assuming no tax/discount separation in Order model
                tax_amount=Decimal('0.00'),
                discount_amount=Decimal('0.00'),
                total_amount=instance.total_amount,
                amount_paid=instance.total_amount,
                change_given=Decimal('0.00'),
                payment_method=payment_method,
                cashier=None,  # No cashier for e-commerce
                seller=None,   # No seller for e-commerce
                ecommerce_order=instance,
                notes=instance.notes
            )
            
            # Create unified sale items
            for order_item in instance.items.all():
                SalesItem.objects.create(
                    sale=unified_sale,
                    product=order_item.product,
                    quantity=order_item.quantity,
                    unit_price=order_item.unit_price,
                    total_price=order_item.total_price,
                    order_item=order_item
                )

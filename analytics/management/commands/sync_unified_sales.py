"""
Management command to sync missing unified Sales records from POSSale and Order models.
This ensures admin and analytics pages show the same data.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from pos.models import POSSale, POSSaleItem
from orders.models import Order, OrderItem
from analytics.models import Sales, SalesItem


class Command(BaseCommand):
    help = 'Sync missing unified Sales records from POSSale and Order models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually creating records',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        created_count = 0
        error_count = 0

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("SYNCING UNIFIED SALES RECORDS"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write("")

        # Sync POS Sales
        self.stdout.write(self.style.WARNING("1. Syncing POS Sales..."))
        completed_pos_sales = POSSale.objects.filter(status='completed')
        
        for pos_sale in completed_pos_sales:
            # Check if unified sale already exists
            if not Sales.objects.filter(pos_sale=pos_sale).exists():
                try:
                    if not dry_run:
                        with transaction.atomic():
                            # Calculate amount_paid
                            amount_paid = pos_sale.total_amount + pos_sale.change_amount
                            
                            # Create unified sale record
                            unified_sale = Sales.objects.create(
                                sale_type='pos',
                                status='completed',
                                customer_name=pos_sale.customer_name or 'Walk-in Customer',
                                customer_phone=pos_sale.customer_phone or '',
                                customer_email=pos_sale.customer_email or '',
                                customer_address='',
                                subtotal=pos_sale.subtotal,
                                tax_amount=pos_sale.tax_amount,
                                discount_amount=pos_sale.discount_amount,
                                total_amount=pos_sale.total_amount,
                                amount_paid=amount_paid,
                                change_given=pos_sale.change_amount,
                                payment_method=pos_sale.payment_method,
                                cashier=pos_sale.cashier,
                                seller=pos_sale.seller,
                                pos_sale=pos_sale,
                                notes=pos_sale.notes,
                                receipt_number=pos_sale.receipt_number or ''
                            )
                            
                            # Create unified sale items
                            for pos_item in pos_sale.items.all():
                                SalesItem.objects.create(
                                    sale=unified_sale,
                                    product=pos_item.product,
                                    quantity=pos_item.quantity,
                                    unit_price=pos_item.unit_price,
                                    total_price=pos_item.total_price,
                                    pos_sale_item=pos_item
                                )
                    
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  Created unified sale for POS sale: {pos_sale.sale_number}"
                    ))
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(
                        f"  Error syncing POS sale {pos_sale.sale_number}: {str(e)}"
                    ))
            else:
                self.stdout.write(f"  Skipped (already exists): {pos_sale.sale_number}")

        self.stdout.write("")

        # Sync E-commerce Orders
        self.stdout.write(self.style.WARNING("2. Syncing E-commerce Orders..."))
        completed_orders = Order.objects.filter(status__in=['confirmed', 'processing', 'shipped', 'delivered'])
        
        for order in completed_orders:
            # Check if unified sale already exists
            if not Sales.objects.filter(ecommerce_order=order).exists():
                try:
                    if not dry_run:
                        with transaction.atomic():
                            # Create unified sale record
                            unified_sale = Sales.objects.create(
                                sale_type='ecommerce',
                                status='completed',
                                customer_name=order.customer_name,
                                customer_phone=order.customer_phone,
                                customer_email=order.customer_email,
                                customer_address=order.shipping_address,
                                subtotal=order.total_amount,
                                tax_amount=Decimal('0.00'),
                                discount_amount=Decimal('0.00'),
                                total_amount=order.total_amount,
                                amount_paid=order.total_amount,
                                change_given=Decimal('0.00'),
                                payment_method='whatsapp',
                                cashier=None,
                                seller=None,
                                ecommerce_order=order,
                                notes=order.notes
                            )
                            
                            # Create unified sale items
                            for order_item in order.items.all():
                                SalesItem.objects.create(
                                    sale=unified_sale,
                                    product=order_item.product,
                                    quantity=order_item.quantity,
                                    unit_price=order_item.unit_price,
                                    total_price=order_item.total_price,
                                    order_item=order_item
                                )
                    
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  Created unified sale for Order: {order.order_number}"
                    ))
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(
                        f"  Error syncing Order {order.order_number}: {str(e)}"
                    ))
            else:
                self.stdout.write(f"  Skipped (already exists): {order.order_number}")

        self.stdout.write("")

        # Summary
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("SYNC SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would create {created_count} unified sales"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created {created_count} unified sales"))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))
        else:
            self.stdout.write(self.style.SUCCESS("No errors!"))
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Admin and analytics pages should now show the same data!"))

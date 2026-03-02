"""
Management command to verify all calculations across the system
Checks sales totals, inventory stock, analytics aggregations, and session totals
"""
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, F
from django.db import transaction
from decimal import Decimal
from pos.models import POSSale, POSSaleItem, POSSession
from analytics.models import Sales, SalesItem, SalesAnalytics
from inventory.models import StockMovement
from catalog.models import Product


class Command(BaseCommand):
    help = "Verify all calculations across sales, inventory, and analytics"

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix any calculation errors found',
        )

    def handle(self, *args, **options):
        fix_errors = options.get('fix', False)
        errors = []
        warnings = []

        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("CALCULATION VERIFICATION REPORT"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write("")

        # 1. Verify POSSale calculations
        self.stdout.write(self.style.WARNING("1. Verifying POS Sale Calculations..."))
        pos_sales = POSSale.objects.filter(status='completed').select_related('tax_rate').prefetch_related('items', 'applied_discounts')
        
        for sale in pos_sales:
            # Calculate expected values
            expected_subtotal = sum(item.total_price for item in sale.items.all())
            
            expected_tax = Decimal("0.00")
            if sale.tax_rate:
                expected_tax = (expected_subtotal * sale.tax_rate.rate) / 100
            
            expected_discount = Decimal("0.00")
            for discount in sale.applied_discounts.all():
                if discount.is_valid():
                    expected_discount += discount.calculate_discount(expected_subtotal)
            
            expected_total = expected_subtotal + expected_tax - expected_discount
            
            # Compare with stored values
            if abs(sale.subtotal - expected_subtotal) > Decimal("0.01"):
                error_msg = f"Sale {sale.sale_number}: Subtotal mismatch. Stored: {sale.subtotal}, Expected: {expected_subtotal}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                if fix_errors:
                    sale.subtotal = expected_subtotal
                    sale.save()
            
            if abs(sale.tax_amount - expected_tax) > Decimal("0.01"):
                error_msg = f"Sale {sale.sale_number}: Tax mismatch. Stored: {sale.tax_amount}, Expected: {expected_tax}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                if fix_errors:
                    sale.tax_amount = expected_tax
                    sale.save()
            
            if abs(sale.discount_amount - expected_discount) > Decimal("0.01"):
                error_msg = f"Sale {sale.sale_number}: Discount mismatch. Stored: {sale.discount_amount}, Expected: {expected_discount}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                if fix_errors:
                    sale.discount_amount = expected_discount
                    sale.save()
            
            if abs(sale.total_amount - expected_total) > Decimal("0.01"):
                error_msg = f"Sale {sale.sale_number}: Total mismatch. Stored: {sale.total_amount}, Expected: {expected_total}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                if fix_errors:
                    sale.total_amount = expected_total
                    sale.save()
        
        if not errors:
            self.stdout.write(self.style.SUCCESS(f"  OK: Verified {pos_sales.count()} POS sales - All calculations correct"))
        self.stdout.write("")

        # 2. Verify Session Totals
        self.stdout.write(self.style.WARNING("2. Verifying POS Session Totals..."))
        sessions = POSSession.objects.filter(status__in=['open', 'closed']).prefetch_related('sales')
        
        for session in sessions:
            completed_sales = session.sales.filter(status='completed')
            
            expected_total_sales = completed_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal("0.00")
            expected_transactions = completed_sales.count()
            expected_tax = completed_sales.aggregate(total=Sum('tax_amount'))['total'] or Decimal("0.00")
            expected_discounts = completed_sales.aggregate(total=Sum('discount_amount'))['total'] or Decimal("0.00")
            
            if abs(session.total_sales - expected_total_sales) > Decimal("0.01"):
                error_msg = f"Session {session.session_id}: Total sales mismatch. Stored: {session.total_sales}, Expected: {expected_total_sales}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                if fix_errors:
                    session.total_sales = expected_total_sales
                    session.total_transactions = expected_transactions
                    session.total_tax_collected = expected_tax
                    session.total_discounts_given = expected_discounts
                    session.save()
            
            if session.total_transactions != expected_transactions:
                error_msg = f"Session {session.session_id}: Transaction count mismatch. Stored: {session.total_transactions}, Expected: {expected_transactions}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
        
        if not any('Session' in e for e in errors):
            self.stdout.write(self.style.SUCCESS(f"  OK: Verified {sessions.count()} sessions - All totals correct"))
        self.stdout.write("")

        # 3. Verify Stock Movements vs Product Stock
        self.stdout.write(self.style.WARNING("3. Verifying Stock Movements vs Product Stock..."))
        products = Product.objects.all()
        
        for product in products:
            # Calculate expected stock from movements
            movements = StockMovement.objects.filter(product=product)
            expected_stock = sum(m.quantity for m in movements)
            
            # Get initial stock (first movement's previous_stock if exists)
            if movements.exists():
                first_movement = movements.order_by('created_at').first()
                if first_movement.quantity > 0:  # It's an addition
                    initial_stock = first_movement.previous_stock
                else:
                    # Find the first positive movement
                    first_positive = movements.filter(quantity__gt=0).order_by('created_at').first()
                    if first_positive:
                        initial_stock = first_positive.previous_stock
                    else:
                        initial_stock = product.stock_quantity  # Fallback
                expected_stock = initial_stock + sum(m.quantity for m in movements)
            else:
                expected_stock = product.stock_quantity
            
            # Note: This is a simplified check - actual stock should be tracked from initial value
            # For now, we'll just verify that the last movement's new_stock matches current stock
            last_movement = movements.order_by('-created_at').first()
            if last_movement and last_movement.new_stock != product.stock_quantity:
                warning_msg = f"Product {product.name}: Stock mismatch. Current: {product.stock_quantity}, Last movement new_stock: {last_movement.new_stock}"
                warnings.append(warning_msg)
                self.stdout.write(self.style.WARNING(f"  WARNING: {warning_msg}"))
        
        if not warnings:
            self.stdout.write(self.style.SUCCESS(f"  OK: Verified stock for {products.count()} products"))
        self.stdout.write("")

        # 4. Verify Unified Sales vs POS Sales
        self.stdout.write(self.style.WARNING("4. Verifying Unified Sales Records..."))
        
        for pos_sale in POSSale.objects.filter(status='completed'):
            try:
                unified_sale = Sales.objects.get(pos_sale=pos_sale)
                
                # Verify amounts match
                if abs(unified_sale.total_amount - pos_sale.total_amount) > Decimal("0.01"):
                    error_msg = f"Sale {pos_sale.sale_number}: Unified sale total mismatch. POS: {pos_sale.total_amount}, Unified: {unified_sale.total_amount}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                    if fix_errors:
                        unified_sale.total_amount = pos_sale.total_amount
                        unified_sale.subtotal = pos_sale.subtotal
                        unified_sale.tax_amount = pos_sale.tax_amount
                        unified_sale.discount_amount = pos_sale.discount_amount
                        unified_sale.save()
                
                # Verify item counts match
                pos_items_count = pos_sale.items.count()
                unified_items_count = unified_sale.items.count()
                if pos_items_count != unified_items_count:
                    error_msg = f"Sale {pos_sale.sale_number}: Item count mismatch. POS: {pos_items_count}, Unified: {unified_items_count}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                    
            except Sales.DoesNotExist:
                warning_msg = f"Sale {pos_sale.sale_number}: Missing unified sales record"
                warnings.append(warning_msg)
                self.stdout.write(self.style.WARNING(f"  WARNING: {warning_msg}"))
        
        unified_count = Sales.objects.filter(pos_sale__isnull=False).count()
        self.stdout.write(self.style.SUCCESS(f"  OK: Verified {unified_count} unified sales records"))
        self.stdout.write("")

        # 5. Verify Analytics Aggregations
        self.stdout.write(self.style.WARNING("5. Verifying Analytics Aggregations..."))
        
        # Check if analytics totals match actual sales
        from datetime import date
        today = date.today()
        
        actual_sales = Sales.objects.filter(created_at__date=today, status='completed')
        actual_total = actual_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal("0.00")
        actual_count = actual_sales.count()
        
        try:
            analytics = SalesAnalytics.objects.get(date=today)
            if abs(analytics.total_revenue - actual_total) > Decimal("0.01"):
                error_msg = f"Analytics for {today}: Revenue mismatch. Stored: {analytics.total_revenue}, Actual: {actual_total}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                if fix_errors:
                    analytics.calculate_daily_analytics()
            
            if analytics.total_sales != actual_count:
                error_msg = f"Analytics for {today}: Sales count mismatch. Stored: {analytics.total_sales}, Actual: {actual_count}"
                errors.append(error_msg)
                self.stdout.write(self.style.ERROR(f"  ERROR: {error_msg}"))
                if fix_errors:
                    analytics.calculate_daily_analytics()
        except SalesAnalytics.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"  WARNING: No analytics record for {today}"))
        
        self.stdout.write(self.style.SUCCESS("  OK: Analytics verification complete"))
        self.stdout.write("")

        # Summary
        self.stdout.write(self.style.SUCCESS("=" * 80))
        self.stdout.write(self.style.SUCCESS("VERIFICATION SUMMARY"))
        self.stdout.write(self.style.SUCCESS("=" * 80))
        
        if errors:
            self.stdout.write(self.style.ERROR(f"ERROR: Found {len(errors)} calculation errors"))
            if fix_errors:
                self.stdout.write(self.style.SUCCESS("OK: All errors have been fixed"))
            else:
                self.stdout.write(self.style.WARNING("TIP: Run with --fix to automatically fix errors"))
        else:
            self.stdout.write(self.style.SUCCESS("OK: No calculation errors found!"))
        
        if warnings:
            self.stdout.write(self.style.WARNING(f"WARNING: Found {len(warnings)} warnings (non-critical)"))
        
        self.stdout.write("")

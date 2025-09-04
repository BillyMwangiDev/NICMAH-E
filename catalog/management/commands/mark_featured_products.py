"""
Django management command to mark popular products as featured.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from catalog.models import Product
from pos.models import POSSaleItem
from orders.models import OrderItem
from django.db.models import Sum, Q


class Command(BaseCommand):
    help = 'Mark popular products as featured based on sales performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to analyze for sales (default: 90)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Number of products to mark as featured (default: 20)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        days = options['days']
        limit = options['limit']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")
        
        # Get date range for analysis
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        self.stdout.write(f"Analyzing sales from {start_date.date()} to {end_date.date()}")
        
        # Get products with sales in the period
        products_with_sales = Product.objects.filter(
            Q(possaleitem__sale__created_at__range=[start_date, end_date]) |
            Q(orderitem__order__created_at__range=[start_date, end_date])
        ).distinct()
        
        # Annotate with sales data
        products = products_with_sales.annotate(
            # POS sales
            pos_quantity=Sum('possaleitem__quantity', 
                             filter=Q(possaleitem__sale__created_at__range=[start_date, end_date],
                                     possaleitem__sale__status='completed')),
            pos_revenue=Sum('possaleitem__total_price',
                           filter=Q(possaleitem__sale__created_at__range=[start_date, end_date],
                                   possaleitem__sale__status='completed')),
            # Online orders
            order_quantity=Sum('orderitem__quantity',
                              filter=Q(orderitem__order__created_at__range=[start_date, end_date],
                                      orderitem__order__status__in=['confirmed', 'completed'])),
            order_revenue=Sum('orderitem__total_price',
                             filter=Q(orderitem__order__created_at__range=[start_date, end_date],
                                     orderitem__order__status__in=['confirmed', 'completed'])),
        ).filter(
            stock_quantity__gt=0,
            is_active=True,
            is_available=True
        )
        
        # Calculate total sales for each product
        product_sales = []
        for product in products:
            total_quantity = (product.pos_quantity or 0) + (product.order_quantity or 0)
            total_revenue = (product.pos_revenue or 0) + (product.order_revenue or 0)
            
            if total_quantity > 0:
                product_sales.append({
                    'product': product,
                    'total_quantity': total_quantity,
                    'total_revenue': total_revenue,
                    'avg_price': total_revenue / total_quantity if total_quantity > 0 else 0
                })
        
        # Sort by total quantity sold (most selling first)
        product_sales.sort(key=lambda x: x['total_quantity'], reverse=True)
        
        # Get top products
        top_products = product_sales[:limit]
        
        if dry_run:
            self.show_dry_run_results(top_products)
        else:
            self.mark_featured_products(top_products)
    
    def show_dry_run_results(self, top_products):
        """Show what would be done without making changes."""
        self.stdout.write("\n" + "="*80)
        self.stdout.write("FEATURED PRODUCTS ANALYSIS")
        self.stdout.write("="*80)
        
        self.stdout.write(f"\nTop {len(top_products)} products by sales volume:")
        for i, item in enumerate(top_products, 1):
            product = item['product']
            self.stdout.write(f"\n{i}. {product.name}")
            self.stdout.write(f"   Category: {product.category.name}")
            self.stdout.write(f"   SKU: {product.sku}")
            self.stdout.write(f"   Price: KSh {product.price}")
            self.stdout.write(f"   Stock: {product.stock_quantity} units")
            self.stdout.write(f"   Total Sold: {item['total_quantity']} units")
            self.stdout.write(f"   Revenue: KSh {item['total_revenue']:,.2f}")
            self.stdout.write(f"   Currently Featured: {'Yes' if product.is_featured else 'No'}")
        
        # Count currently featured products
        currently_featured = Product.objects.filter(is_featured=True).count()
        self.stdout.write(f"\nCurrently featured products: {currently_featured}")
        self.stdout.write(f"Products that would be marked as featured: {len(top_products)}")
    
    def mark_featured_products(self, top_products):
        """Mark products as featured."""
        with transaction.atomic():
            # First, unmark all currently featured products
            Product.objects.filter(is_featured=True).update(is_featured=False)
            self.stdout.write("Unmarked all currently featured products")
            
            # Mark new featured products
            featured_count = 0
            for item in top_products:
                product = item['product']
                product.is_featured = True
                product.save()
                featured_count += 1
                self.stdout.write(f"Marked as featured: {product.name} ({item['total_quantity']} units sold)")
            
            # Summary
            self.stdout.write("\n" + "="*80)
            self.stdout.write("FEATURED PRODUCTS UPDATE COMPLETE")
            self.stdout.write("="*80)
            self.stdout.write(f"Marked {featured_count} products as featured")
            
            # Show final featured products
            featured_products = Product.objects.filter(is_featured=True).order_by('name')
            self.stdout.write(f"\nCurrent featured products:")
            for product in featured_products:
                self.stdout.write(f"  - {product.name} (SKU: {product.sku})")
            
            self.stdout.write(self.style.SUCCESS("\nFeatured products update completed successfully!"))

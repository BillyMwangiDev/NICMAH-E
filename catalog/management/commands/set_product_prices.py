"""
Django management command to set prices for products.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Product, Category
from django.db.models import Q
import json


class Command(BaseCommand):
    help = 'Set prices for products that have zero prices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            help='Set prices for specific category only'
        )
        parser.add_argument(
            '--price-file',
            type=str,
            help='JSON file with product prices'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--list-zero-price',
            action='store_true',
            help='List all products with zero prices'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        category_filter = options['category']
        price_file = options['price_file']
        list_zero_price = options['list_zero_price']
        
        if list_zero_price:
            self.list_zero_price_products(category_filter)
            return
        
        if price_file:
            self.set_prices_from_file(price_file, dry_run)
        else:
            self.interactive_price_setting(category_filter, dry_run)
    
    def list_zero_price_products(self, category_filter):
        """List all products with zero prices."""
        products = Product.objects.filter(price=0, is_active=True)
        
        if category_filter:
            products = products.filter(category__name__icontains=category_filter)
        
        self.stdout.write(f"\nFound {products.count()} products with zero prices:")
        self.stdout.write("=" * 80)
        
        # Group by category
        categories = {}
        for product in products:
            cat_name = product.category.name
            if cat_name not in categories:
                categories[cat_name] = []
            categories[cat_name].append(product)
        
        for category_name, category_products in categories.items():
            self.stdout.write(f"\n{category_name.upper()} ({len(category_products)} products):")
            for product in category_products:
                self.stdout.write(f"  - {product.name} (SKU: {product.sku})")
        
        self.stdout.write(f"\nTotal: {products.count()} products need pricing")
    
    def set_prices_from_file(self, price_file, dry_run):
        """Set prices from a JSON file."""
        try:
            with open(price_file, 'r') as f:
                price_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Price file {price_file} not found"))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"Invalid JSON in {price_file}"))
            return
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No prices will be set")
        
        updated_count = 0
        
        with transaction.atomic():
            for item in price_data:
                sku = item.get('sku')
                price = item.get('price')
                
                if not sku or not price:
                    continue
                
                try:
                    product = Product.objects.get(sku=sku)
                    if product.price == 0:  # Only update if price is currently zero
                        if not dry_run:
                            product.price = price
                            product.save()
                        self.stdout.write(f"Set {product.name} (SKU: {sku}) to KSh {price}")
                        updated_count += 1
                    else:
                        self.stdout.write(f"Skipped {product.name} (SKU: {sku}) - already has price KSh {product.price}")
                except Product.DoesNotExist:
                    self.stdout.write(f"Product with SKU {sku} not found")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {updated_count} products"))
        else:
            self.stdout.write(f"\nWould update {updated_count} products")
    
    def interactive_price_setting(self, category_filter, dry_run):
        """Interactive price setting."""
        products = Product.objects.filter(price=0, is_active=True)
        
        if category_filter:
            products = products.filter(category__name__icontains=category_filter)
        
        if not products.exists():
            self.stdout.write("No products found with zero prices")
            return
        
        self.stdout.write(f"Found {products.count()} products with zero prices")
        
        if dry_run:
            self.stdout.write("DRY RUN MODE - No prices will be set")
        
        # Show categories
        categories = products.values_list('category__name', flat=True).distinct()
        self.stdout.write("\nCategories with products needing prices:")
        for cat in categories:
            cat_count = products.filter(category__name=cat).count()
            self.stdout.write(f"  - {cat}: {cat_count} products")
        
        # Ask for category to work on
        if not category_filter:
            category_name = input("\nEnter category name to set prices for (or 'all'): ").strip()
            if category_name.lower() != 'all':
                products = products.filter(category__name__icontains=category_name)
        
        if not products.exists():
            self.stdout.write("No products found in selected category")
            return
        
        self.stdout.write(f"\nSetting prices for {products.count()} products")
        
        updated_count = 0
        
        for product in products:
            self.stdout.write(f"\n{product.name} (SKU: {product.sku})")
            self.stdout.write(f"Category: {product.category.name}")
            self.stdout.write(f"Current stock: {product.stock_quantity}")
            
            try:
                price_input = input("Enter price (KSh): ").strip()
                if price_input.lower() == 'skip':
                    continue
                
                price = float(price_input)
                if price < 0:
                    self.stdout.write("Price cannot be negative, skipping")
                    continue
                
                if not dry_run:
                    product.price = price
                    product.save()
                
                self.stdout.write(f"Set price to KSh {price}")
                updated_count += 1
                
            except ValueError:
                self.stdout.write("Invalid price, skipping")
            except KeyboardInterrupt:
                self.stdout.write("\nPrice setting interrupted")
                break
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {updated_count} products"))
        else:
            self.stdout.write(f"\nWould update {updated_count} products")


def create_price_template():
    """Create a template JSON file for bulk price setting."""
    template = {
        "instructions": "Set prices for products. Use SKU to identify products.",
        "products": [
            {
                "sku": "EXAMPLE001",
                "price": 100.00,
                "notes": "Optional notes about the product"
            }
        ]
    }
    
    with open('price_template.json', 'w') as f:
        json.dump(template, f, indent=2)
    
    print("Created price_template.json - edit this file and use --price-file to apply prices")


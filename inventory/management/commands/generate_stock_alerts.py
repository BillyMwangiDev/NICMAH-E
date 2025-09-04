"""
Management command to generate sample stock alerts for testing.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from catalog.models import Product
from inventory.models import StockAlert
from decimal import Decimal
import random

User = get_user_model()


class Command(BaseCommand):
    help = "Generate sample stock alerts for testing the notification system"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing stock alerts before generating new ones",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of stock alerts to generate (default: 5)",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            StockAlert.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Cleared all existing stock alerts"))

        # Get products with low stock
        low_stock_products = Product.objects.filter(stock_quantity__lte=10)

        if not low_stock_products.exists():
            self.stdout.write(self.style.WARNING("No products with low stock found. Creating sample products first..."))
            self._create_sample_products()
            low_stock_products = Product.objects.filter(stock_quantity__lte=10)

        # Generate stock alerts
        alerts_created = 0
        for product in low_stock_products[: options["count"]]:
            alert_type = self._get_alert_type(product.stock_quantity)
            priority = self._get_priority(product.stock_quantity)

            alert, created = StockAlert.objects.get_or_create(
                product=product,
                alert_type=alert_type,
                defaults={
                    "current_value": product.stock_quantity,
                    "threshold_value": getattr(product, "min_stock_level", 10),
                    "message": self._generate_message(product, alert_type),
                    "priority": priority,
                    "status": "active",
                },
            )

            if created:
                alerts_created += 1
                self.stdout.write(f"Created {alert_type} alert for {product.name} (Priority: {priority})")
            else:
                self.stdout.write(f"Updated existing {alert_type} alert for {product.name}")

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {alerts_created} stock alerts"))

    def _create_sample_products(self):
        """Create sample products with low stock for testing."""
        from catalog.models import Category

        # Create a sample category if it doesn't exist
        category, _ = Category.objects.get_or_create(
            name="Test Category", defaults={"description": "Test category for stock alerts"}
        )

        # Create sample products with varying stock levels
        sample_products = [
            {"name": "Test Product 1", "stock_quantity": 0, "price": Decimal("10.00")},
            {"name": "Test Product 2", "stock_quantity": 2, "price": Decimal("15.50")},
            {"name": "Test Product 3", "stock_quantity": 5, "price": Decimal("25.00")},
            {"name": "Test Product 4", "stock_quantity": 8, "price": Decimal("8.99")},
            {"name": "Test Product 5", "stock_quantity": 12, "price": Decimal("45.00")},
        ]

        for product_data in sample_products:
            Product.objects.get_or_create(
                name=product_data["name"],
                defaults={
                    "sku": f"TEST-{random.randint(1000, 9999)}",
                    "category": category,
                    "stock_quantity": product_data["stock_quantity"],
                    "price": product_data["price"],
                    "min_stock_level": 10,
                    "reorder_level": 5,
                },
            )

    def _get_alert_type(self, stock_quantity):
        """Determine alert type based on stock quantity."""
        if stock_quantity == 0:
            return "out_of_stock"
        elif stock_quantity <= 5:
            return "low_stock"
        else:
            return "low_stock"

    def _get_priority(self, stock_quantity):
        """Determine priority based on stock quantity."""
        if stock_quantity == 0:
            return "critical"
        elif stock_quantity <= 3:
            return "high"
        elif stock_quantity <= 7:
            return "medium"
        else:
            return "low"

    def _generate_message(self, product, alert_type):
        """Generate alert message based on type."""
        if alert_type == "out_of_stock":
            return f"Critical: {product.name} is completely out of stock. Immediate action required."
        elif alert_type == "low_stock":
            return f"Warning: {product.name} stock is running low. Consider reordering soon."
        else:
            return f"Alert: {product.name} requires attention."

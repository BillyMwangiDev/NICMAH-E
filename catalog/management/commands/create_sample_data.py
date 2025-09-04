"""
Management command to create sample data for testing the UI.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from catalog.models import Category, Product
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = "Create sample categories and products for testing"

    def handle(self, *args, **options):
        self.stdout.write("Creating sample data...")

        # Create categories
        categories_data = [
            {"name": "Animal Feed", "description": "High-quality feed for livestock and pets"},
            {"name": "Veterinary Medicine", "description": "Medicines and supplements for animal health"},
            {"name": "Farming Tools", "description": "Essential tools for modern farming"},
            {"name": "Pet Care", "description": "Products for domestic pet care"},
        ]

        categories = []
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(name=cat_data["name"], defaults=cat_data)
            categories.append(category)
            if created:
                self.stdout.write(f"Created category: {category.name}")
            else:
                self.stdout.write(f"Category already exists: {category.name}")

        # Create products
        products_data = [
            {
                "name": "Premium Chicken Feed",
                "description": "High-protein feed for laying hens and broilers",
                "category": "Animal Feed",
                "price": Decimal("25.99"),
                "stock_quantity": 100,
                "sku": "CHK001",
            },
            {
                "name": "Dairy Cow Supplement",
                "description": "Vitamin and mineral supplement for dairy cows",
                "category": "Veterinary Medicine",
                "price": Decimal("45.50"),
                "stock_quantity": 50,
                "sku": "COW001",
            },
            {
                "name": "Garden Hoe",
                "description": "Sturdy garden hoe for soil preparation",
                "category": "Farming Tools",
                "price": Decimal("15.99"),
                "stock_quantity": 25,
                "sku": "TOOL001",
            },
            {
                "name": "Dog Shampoo",
                "description": "Gentle shampoo for dogs with sensitive skin",
                "category": "Pet Care",
                "price": Decimal("12.99"),
                "stock_quantity": 75,
                "sku": "PET001",
            },
            {
                "name": "Pig Feed Mix",
                "description": "Balanced feed mix for growing pigs",
                "category": "Animal Feed",
                "price": Decimal("35.00"),
                "stock_quantity": 60,
                "sku": "PIG001",
            },
            {
                "name": "Cattle Dewormer",
                "description": "Effective deworming treatment for cattle",
                "category": "Veterinary Medicine",
                "price": Decimal("28.75"),
                "stock_quantity": 40,
                "sku": "COW002",
            },
        ]

        for prod_data in products_data:
            category_name = prod_data.pop("category")
            category = next(cat for cat in categories if cat.name == category_name)

            product, created = Product.objects.get_or_create(
                sku=prod_data["sku"], defaults={**prod_data, "category": category}
            )

            if created:
                self.stdout.write(f"Created product: {product.name} - ${product.price}")
            else:
                self.stdout.write(f"Product already exists: {product.name}")

        self.stdout.write(self.style.SUCCESS("Successfully created sample data!"))

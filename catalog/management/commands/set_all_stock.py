"""
Set all product stock quantities to a specified value (default: 50)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from catalog.models import Product


class Command(BaseCommand):
    help = "Set all product stock quantities to a specified value (default: 50)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--value",
            type=int,
            default=50,
            help="Stock quantity value to set for all products (default: 50)",
        )
        parser.add_argument(
            "--only-zero",
            action="store_true",
            help="Only set products that currently have zero stock",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without saving",
        )

    def handle(self, *args, **options):
        value = options["value"]
        only_zero = options["only_zero"]
        dry_run = options["dry_run"]

        qs = Product.objects.all()
        if only_zero:
            qs = qs.filter(stock_quantity=0)

        count = qs.count()
        self.stdout.write(f"Found {count} products to update.")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would set stock_quantity to {value} for {count} products"
                )
            )
            return

        with transaction.atomic():
            updated = qs.update(stock_quantity=value)

        self.stdout.write(self.style.SUCCESS(f"Updated stock for {updated} products to {value}."))


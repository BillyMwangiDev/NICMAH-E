"""
Import product package_size and price from a CSV file.
CSV Columns required:
- sku (or name)
- package_size (e.g., 100 ml, 180 ml, 200 ml, 1 L)
- price (numeric)
Optional: category

Usage:
python manage.py import_sizes_prices path/to/file.csv [--dry-run]
"""

import csv
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from catalog.models import Product


class Command(BaseCommand):
    help = "Import product package_size and price from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the CSV file")
        parser.add_argument("--dry-run", action="store_true", help="Do not save changes")
        parser.add_argument(
            "--match-by",
            choices=["sku", "name"],
            default="sku",
            help="Field to match products by (default: sku)",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]
        match_by = options["match_by"]

        try:
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required = {"package_size", "price"}
                if match_by == "sku":
                    required.add("sku")
                else:
                    required.add("name")
                missing = required - set(reader.fieldnames or [])
                if missing:
                    raise CommandError(f"Missing required columns: {', '.join(missing)}")

                updated = 0
                errors = 0

                @transaction.atomic
                def process():
                    nonlocal updated, errors
                    for row in reader:
                        identifier = row.get(match_by, "").strip()
                        package_size = (row.get("package_size") or "").strip()
                        price_raw = (row.get("price") or "").strip()

                        if not identifier:
                            self.stdout.write(self.style.WARNING("Skipping row with empty identifier"))
                            errors += 1
                            continue

                        try:
                            price = Decimal(price_raw)
                        except (InvalidOperation, TypeError):
                            self.stdout.write(self.style.WARNING(f"Invalid price for {identifier}: {price_raw}"))
                            errors += 1
                            continue

                        try:
                            if match_by == "sku":
                                product = Product.objects.get(sku=identifier)
                            else:
                                product = Product.objects.get(name__iexact=identifier)
                        except Product.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f"Product not found: {identifier}"))
                            errors += 1
                            continue

                        changes = []
                        if package_size and product.package_size != package_size:
                            product.package_size = package_size
                            changes.append(f"package_size='{package_size}'")
                        if product.price != price:
                            product.price = price
                            changes.append(f"price={price}")

                        if not changes:
                            continue

                        if dry_run:
                            self.stdout.write(f"Would update {product.sku or product.name}: {', '.join(changes)}")
                        else:
                            product.save()
                            updated += 1
                            self.stdout.write(f"Updated {product.sku or product.name}: {', '.join(changes)}")

                process()

        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_path}")

        summary = f"Updated {updated} products with {errors} errors"
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - " + summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))


"""
Import product package sizes from Excel where:
- Product name is in column 'Unnamed: 3' (as observed in the provided file)
- Package size is in column 'QUANTITY' (values like '50ML', '100ML', '500 ML')

Matching strategy:
- Try exact name (case-insensitive) match on Product.name
- If no exact match, try partial contains match
- Optionally match by SKU if a 'SKU' column exists

Usage:
python manage.py import_package_sizes "C:/Users/USER/Downloads/Copy of PRODCTS.xlsx" --sheet Sheet1 [--dry-run]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from catalog.models import Product

try:
    import pandas as pd
except Exception:
    pd = None


class Command(BaseCommand):
    help = "Import product package sizes from an Excel sheet into Product.package_size"

    def add_arguments(self, parser):
        parser.add_argument("excel_path", type=str, help="Path to Excel file")
        parser.add_argument("--sheet", type=str, default=None, help="Worksheet name (optional)")
        parser.add_argument("--dry-run", action="store_true", help="Preview without saving")

    def handle(self, *args, **options):
        if pd is None:
            raise CommandError("pandas is required. Install with: pip install pandas openpyxl")

        excel_path = options["excel_path"]
        sheet = options["sheet"]
        dry_run = options["dry_run"]

        try:
            df = pd.read_excel(excel_path, sheet_name=sheet or 0)
        except FileNotFoundError:
            raise CommandError(f"Excel file not found: {excel_path}")
        except Exception as exc:
            raise CommandError(f"Failed reading Excel: {exc}")

        df.columns = [str(c).strip() for c in df.columns]

        name_col = None
        for candidate in ["Unnamed: 3", "Product Name", "NAME", "name", "DESCRIPTION", "Description"]:
            if candidate in df.columns:
                name_col = candidate
                break
        if name_col is None:
            raise CommandError("Could not find a product name column (e.g., 'Unnamed: 3')")

        size_col = None
        for candidate in ["QUANTITY", "Quantity", "quantity"]:
            if candidate in df.columns:
                size_col = candidate
                break
        if size_col is None:
            raise CommandError("Could not find a size column (e.g., 'QUANTITY')")

        sku_col = None
        for candidate in ["SKU", "sku"]:
            if candidate in df.columns:
                sku_col = candidate
                break

        updated = 0
        missing = 0
        skipped = 0

        @transaction.atomic
        def process():
            nonlocal updated, missing, skipped
            for _, row in df.iterrows():
                raw_name = str(row.get(name_col) or "").strip()
                raw_size = str(row.get(size_col) or "").strip()
                if not raw_name:
                    skipped += 1
                    continue
                if not raw_size:
                    skipped += 1
                    continue

                # Normalize size like '500 ML' -> '500 ml'
                normalized_size = " ".join(raw_size.split()).lower()
                normalized_size = normalized_size.replace("ml", " ml").replace("  ", " ").strip()
                # Fix cases like '50ML' -> '50 ml'
                if normalized_size.endswith("ml") and not normalized_size[:-2].strip().endswith(" "):
                    # already handled by split, but keep consistent casing
                    pass

                product = None
                identifier = None

                if sku_col:
                    sku_val = str(row.get(sku_col) or "").strip()
                    if sku_val:
                        identifier = sku_val
                        product = Product.objects.filter(sku=sku_val).first()

                if product is None:
                    # Exact name match
                    product = Product.objects.filter(name__iexact=raw_name).first()

                if product is None:
                    # Partial contains match
                    product = (
                        Product.objects.filter(Q(name__icontains=raw_name)).order_by("-created_at").first()
                    )

                if product is None:
                    missing += 1
                    continue

                if (product.package_size or "").strip().lower() != normalized_size:
                    if dry_run:
                        self.stdout.write(f"Would set {product.sku or product.name} package_size: '{product.package_size}' -> '{normalized_size}'")
                    else:
                        product.package_size = normalized_size
                        product.save(update_fields=["package_size", "updated_at"])
                        updated += 1

        process()

        summary = f"Updated: {updated}, Missing matches: {missing}, Skipped rows: {skipped}"
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - " + summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))


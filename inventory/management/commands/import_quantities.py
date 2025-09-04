"""
Import product quantities from an Excel file to update stock_quantity.

- Matches by SKU first; if missing, falls back to case-insensitive name match.
- Expects a column named one of: QUANTITY, Quantity, quantity, Current Stock
- Also looks for columns: SKU (or sku), NAME (or Product Name, name)
- Optional: SHEET name via --sheet

Usage:
python manage.py import_quantities "C:/Users/USER/Downloads/Copy of PRODCTS.xlsx" --sheet Sheet1 [--dry-run]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from catalog.models import Product

try:
    import pandas as pd
except Exception as exc:
    pd = None


class Command(BaseCommand):
    help = "Import product quantities from an Excel file and update stock_quantity"

    def add_arguments(self, parser):
        parser.add_argument("excel_path", type=str, help="Path to the Excel file (.xlsx)")
        parser.add_argument("--sheet", type=str, default=None, help="Worksheet name (optional)")
        parser.add_argument("--dry-run", action="store_true", help="Do not persist changes")

    def handle(self, *args, **options):
        if pd is None:
            raise CommandError(
                "pandas is required. Install with: pip install pandas openpyxl"
            )

        excel_path = options["excel_path"]
        sheet = options["sheet"]
        dry_run = options["dry_run"]

        try:
            df = pd.read_excel(excel_path, sheet_name=sheet or 0)
        except FileNotFoundError:
            raise CommandError(f"Excel file not found: {excel_path}")
        except Exception as exc:
            raise CommandError(f"Failed reading Excel: {exc}")

        # Normalize columns
        df.columns = [str(c).strip() for c in df.columns]
        col_map = {c.lower(): c for c in df.columns}

        # Determine identifier and quantity columns
        sku_col = None
        for key in ["sku", "SKU"]:
            if key in df.columns:
                sku_col = key
                break
        if sku_col is None and "sku" in col_map:
            sku_col = col_map["sku"]

        name_col = None
        for candidate in ["NAME", "Product Name", "PRODUCT_NAME", "Description", "DESCRIPTION", "name"]:
            if candidate in df.columns:
                name_col = candidate
                break
        if name_col is None:
            for key in ["product name", "description"]:
                if key in col_map:
                    name_col = col_map[key]
                    break

        qty_col = None
        for candidate in ["QUANTITY", "Quantity", "quantity", "Current Stock", "CURRENT STOCK"]:
            if candidate in df.columns:
                qty_col = candidate
                break
        if qty_col is None:
            for key in ["current stock", "qty", "stock"]:
                if key in col_map:
                    qty_col = col_map[key]
                    break

        if qty_col is None:
            raise CommandError("Could not find a quantity column (e.g., QUANTITY)")

        updated = 0
        missing = 0
        errors = 0

        @transaction.atomic
        def process():
            nonlocal updated, missing, errors
            for _, row in df.iterrows():
                try:
                    val = pd.to_numeric(row.get(qty_col), errors="coerce")
                    if pd.isna(val):
                        quantity = 0
                    else:
                        quantity = int(float(val))
                except Exception:
                    errors += 1
                    continue

                product = None
                identifier = None

                if sku_col:
                    sku_val = str(row.get(sku_col) or "").strip()
                    if sku_val:
                        identifier = sku_val
                        product = Product.objects.filter(sku=sku_val).first()

                if product is None and name_col:
                    name_val = str(row.get(name_col) or "").strip()
                    if name_val:
                        identifier = identifier or name_val
                        product = Product.objects.filter(name__iexact=name_val).first()

                if product is None:
                    missing += 1
                    continue

                if product.stock_quantity != quantity:
                    if dry_run:
                        self.stdout.write(
                            f"Would set {product.sku or product.name} stock_quantity: {product.stock_quantity} -> {quantity}"
                        )
                    else:
                        product.stock_quantity = quantity
                        product.save(update_fields=["stock_quantity", "updated_at"])
                        updated += 1

        process()

        summary = f"Updated: {updated}, Missing matches: {missing}, Errors: {errors}"
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - " + summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))

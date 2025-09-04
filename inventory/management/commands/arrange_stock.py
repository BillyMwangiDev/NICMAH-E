"""
Django management command to arrange stock data from Excel files.
"""

import pandas as pd
from datetime import date
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from catalog.models import Product, Category
from inventory.models import StockMovement, InventoryTransaction
import os
import re

User = get_user_model()


class Command(BaseCommand):
    help = 'Arrange stock data from Excel file and update database'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the Excel file (e.g., "Copy of PRODCTS.xlsx")'
        )
        parser.add_argument(
            '--sheet-name',
            type=str,
            default='Sheet1',
            help='Sheet name in Excel file (default: Sheet1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )
        parser.add_argument(
            '--create-categories',
            action='store_true',
            help='Create new categories if they don\'t exist'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID for tracking stock movements (default: first superuser)'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        sheet_name = options['sheet_name']
        dry_run = options['dry_run']
        create_categories = options['create_categories']
        user_id = options['user_id']

        # Validate file exists
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        # Get user for tracking
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f"User with ID {user_id} not found")
        else:
            # Get first superuser
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                raise CommandError("No superuser found. Please create one or specify --user-id")

        self.stdout.write(f"Processing file: {file_path}")
        self.stdout.write(f"Sheet name: {sheet_name}")
        self.stdout.write(f"User: {user.username}")
        self.stdout.write(f"Dry run: {dry_run}")

        try:
            # Load Excel file
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            self.stdout.write(f"Loaded {len(df)} rows from Excel file")

            # Process the data
            processed_data = self.process_excel_data(df)
            
            if dry_run:
                self.show_dry_run_results(processed_data)
            else:
                self.update_database(processed_data, user, create_categories)

        except Exception as e:
            raise CommandError(f"Error processing file: {str(e)}")

    def process_excel_data(self, df):
        """Process Excel data according to the user's requirements."""
        
        # Combine columns into product name
        df["PRODUCT_NAME"] = df[["DESCRIPTION", "Unnamed: 3"]].fillna("").agg(" ".join, axis=1).str.strip()
        df = df[df["PRODUCT_NAME"] != ""].reset_index(drop=True)

        # Generate SKUs
        df["SKU"] = [
            (name[:3].upper() if len(name) >= 3 else name.upper()).ljust(3, "X") + str(i+1).zfill(3)
            for i, name in enumerate(df["PRODUCT_NAME"])
        ]

        # Map categories from DESCRIPTION column
        df["Category"] = df["DESCRIPTION"].fillna("")

        # Unit Prices (online prices for known products)
        price_lookup = {
            "ALAMYCIN 10": 213,
            "ALAMYCIN 20": 450,
            "OPTICLOX": 1100,
            "BENDAMEC": 198
        }

        def get_price(name):
            for key, price in price_lookup.items():
                if key in name.upper():
                    return price
            return 0

        # Build final structured DataFrame
        df_final = pd.DataFrame({
            "Product ID": [f"P{str(i+1).zfill(3)}" for i in range(len(df))],
            "Product Name": df["PRODUCT_NAME"],
            "SKU": df["SKU"],
            "Category": df["Category"],
            "Current Stock": pd.to_numeric(df["QUANTITY"], errors="coerce").fillna(0),
            "Minimum Stock": 10,
            "Unit Price": df["PRODUCT_NAME"].apply(get_price),
            "Last Updated": date.today()
        })

        # Calculate total value and stock status
        df_final["Total Value"] = df_final["Current Stock"] * df_final["Unit Price"]
        df_final["Status"] = df_final.apply(
            lambda x: "In Stock" if x["Current Stock"] >= x["Minimum Stock"]
            else "Low Stock" if x["Current Stock"] > 0
            else "Missing",
            axis=1
        )

        return df_final

    def show_dry_run_results(self, df):
        """Show what would be done without making changes."""
        self.stdout.write("\n" + "="*80)
        self.stdout.write("DRY RUN RESULTS")
        self.stdout.write("="*80)
        
        self.stdout.write(f"\nTotal products to process: {len(df)}")
        
        # Summary by status
        status_counts = df["Status"].value_counts()
        self.stdout.write("\nStock Status Summary:")
        for status, count in status_counts.items():
            self.stdout.write(f"  {status}: {count}")
        
        # Summary by category
        category_counts = df["Category"].value_counts()
        self.stdout.write("\nCategory Summary:")
        for category, count in category_counts.head(10).items():
            self.stdout.write(f"  {category}: {count}")
        
        # Financial summary
        total_value = df["Total Value"].sum()
        total_stock = df["Current Stock"].sum()
        self.stdout.write(f"\nFinancial Summary:")
        self.stdout.write(f"  Total Stock Value: KSh {total_value:,.2f}")
        self.stdout.write(f"  Total Stock Quantity: {total_stock:,}")
        
        # Sample data
        self.stdout.write(f"\nSample Products (first 5):")
        for _, row in df.head().iterrows():
            self.stdout.write(f"  {row['Product Name']} - Stock: {row['Current Stock']} - Price: KSh {row['Unit Price']}")

    def update_database(self, df, user, create_categories):
        """Update the database with processed data."""
        
        with transaction.atomic():
            created_products = 0
            updated_products = 0
            created_categories = 0
            
            for _, row in df.iterrows():
                # Get or create category
                category_name = row["Category"].strip()
                if not category_name:
                    category_name = "Uncategorized"
                
                category, category_created = Category.objects.get_or_create(
                    name=category_name,
                    defaults={
                        'description': f'Category for {category_name}',
                        'is_active': True
                    }
                )
                
                if category_created and create_categories:
                    created_categories += 1
                
                # Generate unique slug
                base_slug = slugify(row["Product Name"])
                slug = base_slug
                counter = 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                # Get or create product
                product, product_created = Product.objects.get_or_create(
                    sku=row["SKU"],
                    defaults={
                        'name': row["Product Name"],
                        'slug': slug,
                        'description': f'Product: {row["Product Name"]}',
                        'category': category,
                        'price': row["Unit Price"],
                        'stock_quantity': row["Current Stock"],
                        'min_stock_level': row["Minimum Stock"],
                        'is_active': True,
                        'is_available': True
                    }
                )
                
                if product_created:
                    created_products += 1
                    self.stdout.write(f"Created product: {product.name} (SKU: {product.sku})")
                else:
                    # Update existing product
                    old_stock = product.stock_quantity
                    product.stock_quantity = row["Current Stock"]
                    product.price = row["Unit Price"]
                    product.min_stock_level = row["Minimum Stock"]
                    product.save()
                    updated_products += 1
                    
                    # Create stock movement record
                    if old_stock != row["Current Stock"]:
                        StockMovement.objects.create(
                            product=product,
                            movement_type=StockMovement.MovementType.ADJUSTMENT,
                            quantity=row["Current Stock"] - old_stock,
                            previous_stock=old_stock,
                            new_stock=row["Current Stock"],
                            reference_number=f"EXCEL_IMPORT_{date.today()}",
                            reference_type="Excel Import",
                            user=user,
                            notes=f"Stock updated from Excel import. Previous: {old_stock}, New: {row['Current Stock']}"
                        )
                        
                        # Create inventory transaction
                        InventoryTransaction.objects.create(
                            product=product,
                            transaction_type=InventoryTransaction.TransactionType.ADJUST,
                            quantity=row["Current Stock"] - old_stock,
                            unit_cost=row["Unit Price"],
                            total_cost=abs(row["Current Stock"] - old_stock) * row["Unit Price"],
                            previous_stock=old_stock,
                            new_stock=row["Current Stock"],
                            reference_number=f"EXCEL_IMPORT_{date.today()}",
                            reference_type="Excel Import",
                            user=user,
                            notes=f"Stock adjustment from Excel import"
                        )
            
            # Summary
            self.stdout.write("\n" + "="*80)
            self.stdout.write("DATABASE UPDATE COMPLETE")
            self.stdout.write("="*80)
            self.stdout.write(f"Created categories: {created_categories}")
            self.stdout.write(f"Created products: {created_products}")
            self.stdout.write(f"Updated products: {updated_products}")
            
            # Export processed data to Excel
            output_file = f"Arranged_Stock_Data_{date.today()}.xlsx"
            df.to_excel(output_file, index=False)
            self.stdout.write(f"\nProcessed data exported to: {output_file}")
            
            self.stdout.write(self.style.SUCCESS("\nStock arrangement completed successfully!"))

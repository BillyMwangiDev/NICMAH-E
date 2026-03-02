"""
Inventory management views with Excel import/export functionality and SKU scanner support.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Sum, Q, F
from django.utils import timezone
from decimal import Decimal
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
import io
from django.urls import reverse

from .models import StockMovement, StockAlert, PurchaseOrder, Document, DocumentItem, DocumentTemplate
from catalog.models import Category, Product
from .document_generation import DOCUMENTS_AVAILABLE, generate_receipt_pdf, generate_quotation_pdf, generate_invoice_pdf, send_document_email, print_document


@login_required
def dashboard(request):
    """Inventory dashboard with stock overview and alerts."""
    # Get stock statistics
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(stock_quantity__lte=F("min_stock_level")).count()
    out_of_stock = Product.objects.filter(stock_quantity=0).count()

    # Get recent stock movements
    recent_movements = StockMovement.objects.select_related("product", "user").order_by("-created_at")[:10]

    # Get low stock alerts
    low_stock_alerts = Product.objects.filter(stock_quantity__lte=F("min_stock_level")).order_by("stock_quantity")[:5]

    # Get stock value
    total_stock_value = Product.objects.aggregate(total_value=Sum(F("stock_quantity") * F("price")))[
        "total_value"
    ] or Decimal("0.00")

    # Get additional statistics
    in_stock_products = Product.objects.filter(stock_quantity__gt=F("min_stock_level")).count()
    total_categories = Category.objects.count()
    
    # Get recent movements count
    recent_movements_count = StockMovement.objects.count()
    today_movements = StockMovement.objects.filter(created_at__date=timezone.now().date()).count()
    
    context = {
        "total_products": total_products,
        "low_stock_products": low_stock_products,
        "out_of_stock": out_of_stock,
        "in_stock_products": in_stock_products,
        "total_stock_value": total_stock_value,
        "total_categories": total_categories,
        "recent_movements": recent_movements,
        "recent_movements_count": recent_movements_count,
        "today_movements": today_movements,
        "low_stock_alerts": low_stock_alerts,
    }

    return render(request, "inventory/dashboard.html", context)


@login_required
def sku_scanner(request):
    """SKU scanner interface for stock receiving and inventory management."""
    if request.method == "POST":
        sku = request.POST.get("sku", "").strip()
        product_name = request.POST.get("product_name", "").strip()
        action = request.POST.get("action", "lookup")

        if not sku and not product_name:
            messages.error(request, "Please enter or scan a SKU or product name.")
            return render(request, "inventory/sku_scanner.html")

        try:
            # Try to find product by SKU first, then by name
            if sku:
                product = Product.objects.get(sku=sku)
            else:
                # Find by name (case-insensitive)
                product = Product.objects.filter(name__iexact=product_name).first()
                if not product:
                    # Try partial match
                    product = Product.objects.filter(name__icontains=product_name).first()
                    if not product:
                        messages.error(request, f'Product "{product_name}" not found.')
                        return render(
                            request, "inventory/sku_scanner.html", {"scanned_sku": sku, "product_name": product_name}
                        )

            if action == "lookup":
                # Just show product info
                context = {"product": product, "scanned_sku": sku, "action": action}
                return render(request, "inventory/sku_scanner.html", context)

            elif action == "receive_stock":
                # Stock receiving workflow
                quantity = int(request.POST.get("quantity", 1))
                notes = request.POST.get("notes", "Stock received via scanner")

                with transaction.atomic():
                    # Update product stock
                    product.stock_quantity += quantity
                    product.save()

                    # Create stock movement record
                    StockMovement.objects.create(
                        product=product,
                        movement_type="purchase",
                        quantity=quantity,
                        previous_stock=product.stock_quantity - quantity,
                        new_stock=product.stock_quantity,
                        reference_number=f'SCAN_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                        notes=notes,
                        user=request.user,
                    )

                messages.success(request, f"Successfully received {quantity} units of {product.name}")
                return redirect("inventory:sku_scanner")

            elif action == "adjust_stock":
                # Stock adjustment workflow
                new_quantity = int(request.POST.get("new_quantity", 0))
                adjustment_type = request.POST.get("adjustment_type", "set")
                notes = request.POST.get("notes", "Stock adjusted via scanner")

                with transaction.atomic():
                    old_quantity = product.stock_quantity

                    if adjustment_type == "set":
                        adjustment = new_quantity - old_quantity
                        product.stock_quantity = new_quantity
                    elif adjustment_type == "add":
                        adjustment = new_quantity
                        product.stock_quantity += new_quantity
                    elif adjustment_type == "subtract":
                        adjustment = -new_quantity
                        product.stock_quantity = max(0, product.stock_quantity - new_quantity)

                    product.save()

                    # Create stock movement record
                    StockMovement.objects.create(
                        product=product,
                        movement_type="adjustment",
                        quantity=adjustment,
                        previous_stock=old_quantity,
                        new_stock=product.stock_quantity,
                        reference_number=f'ADJUST_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                        notes=f"{notes} (Old: {old_quantity}, New: {product.stock_quantity})",
                        user=request.user,
                    )

                messages.success(request, f"Stock adjusted for {product.name}. New quantity: {product.stock_quantity}")
                return redirect("inventory:sku_scanner")

        except Product.DoesNotExist:
            messages.error(request, f'Product with SKU "{sku}" not found.')
            return render(request, "inventory/sku_scanner.html", {"scanned_sku": sku})
        except ValueError:
            messages.error(request, "Invalid quantity value.")
            return render(request, "inventory/sku_scanner.html", {"scanned_sku": sku})
        except Exception as e:
            messages.error(request, f"Error processing request: {str(e)}")
            return render(request, "inventory/sku_scanner.html", {"scanned_sku": sku})

    return render(request, "inventory/sku_scanner.html")


@login_required
def quick_stock_receiving(request):
    """Quick stock receiving interface optimized for scanner use."""
    if request.method == "POST":
        sku = request.POST.get("sku", "").strip()
        product_name = request.POST.get("product_name", "").strip()
        quantity = int(request.POST.get("quantity", 1))

        if not sku and not product_name:
            return JsonResponse({"success": False, "error": "SKU or product name required"})

        try:
            # Try to find product by SKU first, then by name
            if sku:
                product = Product.objects.get(sku=sku)
            else:
                # Find by name (case-insensitive)
                product = Product.objects.filter(name__iexact=product_name).first()
                if not product:
                    # Try partial match
                    product = Product.objects.filter(name__icontains=product_name).first()
                    if not product:
                        return JsonResponse({"success": False, "error": f'Product "{product_name}" not found'})

            with transaction.atomic():
                # Update product stock
                product.stock_quantity += quantity
                product.save()

                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    movement_type="purchase",
                    quantity=quantity,
                    previous_stock=product.stock_quantity - quantity,
                    new_stock=product.stock_quantity,
                    reference_number=f'QUICK_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                    notes="Quick stock receiving via scanner",
                    user=request.user,
                )

            return JsonResponse(
                {
                    "success": True,
                    "product": {
                        "name": product.name,
                        "sku": product.sku,
                        "new_stock": product.stock_quantity,
                        "category": product.category.name if product.category else "Uncategorized",
                    },
                    "message": f"Received {quantity} units of {product.name}",
                }
            )

        except Product.DoesNotExist:
            return JsonResponse({"success": False, "error": f'Product with SKU "{sku}" not found'})
        except ValueError:
            return JsonResponse({"success": False, "error": "Invalid quantity value"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return render(request, "inventory/quick_stock_receiving.html")


@login_required
def record_purchase(request):
    """Record when products are purchased (bought) and add to stock."""
    if request.method == "POST":
        product_name = request.POST.get("product_name", "").strip()
        quantity = int(request.POST.get("quantity", 1))
        unit_cost = Decimal(request.POST.get("unit_cost", "0.00"))
        supplier = request.POST.get("supplier", "").strip()
        notes = request.POST.get("notes", "Product purchased")

        if not product_name:
            messages.error(request, "Product name is required.")
            return render(request, "inventory/record_purchase.html")

        try:
            # Try to find existing product by name
            product = Product.objects.filter(name__iexact=product_name).first()

            if not product:
                # Create new product if it doesn't exist
                category = Category.objects.first()  # Default category
                product = Product.objects.create(
                    name=product_name,
                    price=unit_cost * Decimal("1.3"),  # 30% markup for retail price
                    stock_quantity=quantity,
                    min_stock_level=5,
                    category=category,
                )
                messages.success(request, f'New product "{product_name}" created and {quantity} units added to stock.')
            else:
                # Update existing product stock
                product.stock_quantity += quantity
                product.save()
                messages.success(
                    request, f'Added {quantity} units to "{product_name}". New stock: {product.stock_quantity}'
                )

            # Create stock movement record
            StockMovement.objects.create(
                product=product,
                movement_type="purchase",
                quantity=quantity,
                previous_stock=product.stock_quantity - quantity,
                new_stock=product.stock_quantity,
                reference_number=f'PURCHASE_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                notes=f"{notes} - Supplier: {supplier}, Cost: ${unit_cost}/unit",
                user=request.user,
            )

            return redirect("inventory:record_purchase")

        except ValueError:
            messages.error(request, "Invalid quantity or cost value.")
        except Exception as e:
            messages.error(request, f"Error recording purchase: {str(e)}")

    # Get recent purchases for display
    recent_purchases = (
        StockMovement.objects.filter(movement_type="purchased")
        .select_related("product", "user")
        .order_by("-created_at")[:10]
    )

    context = {
        "recent_purchases": recent_purchases,
    }

    return render(request, "inventory/record_purchase.html", context)


@login_required
def stock_movements(request):
    """View all stock movements with filtering and export."""
    movements = StockMovement.objects.select_related("product", "user").order_by("-created_at")

    # Filtering
    product_filter = request.GET.get("product")
    movement_type = request.GET.get("type")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if product_filter:
        # Support both product ID and product name search
        try:
            product_id = int(product_filter)
            movements = movements.filter(product_id=product_id)
        except (ValueError, TypeError):
            movements = movements.filter(product__name__icontains=product_filter)
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    if date_from:
        movements = movements.filter(created_at__date__gte=date_from)
    if date_to:
        movements = movements.filter(created_at__date__lte=date_to)

    # Pagination
    paginator = Paginator(movements, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "stock_movements": page_obj,
        "total_movements": movements.count(),
        "products": Product.objects.all(),
    }

    return render(request, "inventory/stock_movements.html", context)


@login_required
def export_stock_data(request):
    """Export stock data to Excel."""
    try:
        # Get stock data
        products = Product.objects.select_related("category").all()

        # Create DataFrame
        data = []
        for product in products:
            data.append(
                {
                    "Product ID": product.id,
                    "Product Name": product.name,
                    "SKU": product.sku,
                    "Category": product.category.name if product.category else "",
                    "Current Stock": product.stock_quantity,
                    "Minimum Stock": product.min_stock_level,
                    "Unit Price": float(product.price),
                    "Total Value": float(product.stock_quantity * product.price),
                    "Status": "Low Stock" if product.stock_quantity <= product.min_stock_level else "OK",
                    "Last Updated": product.updated_at.strftime("%Y-%m-%d %H:%M"),
                }
            )

        df = pd.DataFrame(data)

        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Stock Data", index=False)

            # Get the worksheet
            worksheet = writer.sheets["Stock Data"]

            # Style the header row
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")

            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except (ValueError, TypeError):
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        # Create response
        response = HttpResponse(
            output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="stock_data_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
        )

        return response

    except Exception as e:
        messages.error(request, f"Error exporting stock data: {str(e)}")
        return redirect("inventory:dashboard")


@login_required
def import_stock_data(request):
    """Import stock data from Excel file with improved error handling and format detection."""
    if request.method == "POST":
        try:
            excel_file = request.FILES.get("excel_file")
            if not excel_file:
                messages.error(request, "Please select an Excel file to import.")
                return redirect("inventory:import_stock_data")

            # Validate file extension
            if not excel_file.name.lower().endswith(('.xlsx', '.xls')):
                messages.error(request, "Please select a valid Excel file (.xlsx or .xls)")
                return redirect("inventory:import_stock_data")

            # Read Excel file with better error handling
            try:
                # Try to read with pandas
                df = pd.read_excel(excel_file, engine='openpyxl')
            except Exception as e:
                try:
                    # Fallback to xlrd for older Excel files
                    excel_file.seek(0)
                    df = pd.read_excel(excel_file, engine='xlrd')
                except Exception as e2:
                    messages.error(request, f"Error reading Excel file: {str(e2)}")
                    return redirect("inventory:import_stock_data")

            # Check if DataFrame is empty
            if df.empty:
                messages.error(request, "The Excel file appears to be empty or has no data.")
                return redirect("inventory:import_stock_data")

            # Normalize column names for flexible matching
            original_columns = list(df.columns)
            df.columns = [str(c).strip() for c in df.columns]
            
            # Create case-insensitive column mapping
            column_map = {}
            for col in df.columns:
                col_lower = col.lower().strip()
                column_map[col_lower] = col
            
            # Detect format and process accordingly
            success_count = 0
            error_count = 0
            errors = []
            
            # Format 1: User's format (DESCRIPTION, Unnamed: 3, QUANTITY)
            if any(key in column_map for key in ['description', 'quantity']):
                success_count, error_count, errors = process_user_format(df, column_map, request.user)
            
            # Format 2: Standard format (Product Name, SKU, Current Stock, Unit Price)
            elif any(key in column_map for key in ['product name', 'sku', 'current stock', 'unit price']):
                success_count, error_count, errors = process_standard_format(df, column_map, request.user)
            
            # Format 3: Try to auto-detect columns
            else:
                success_count, error_count, errors = auto_detect_format(df, column_map, request.user)

            # Show results
            if success_count > 0:
                messages.success(request, f"Successfully imported {success_count} products.")
            if error_count > 0:
                messages.warning(request, f"{error_count} products had errors during import.")
                for error in errors[:5]:  # Show first 5 errors
                    messages.warning(request, error)
                if len(errors) > 5:
                    messages.warning(request, f"... and {len(errors) - 5} more errors.")

            return redirect("inventory:import_stock_data")

        except Exception as e:
            messages.error(request, f"An error occurred during import: {str(e)}")
            return redirect("inventory:import_stock_data")

    return render(request, "inventory/import_stock.html")


def process_user_format(df, column_map, user):
    """Process the user's specific Excel format."""
    success_count = 0
    error_count = 0
    errors = []

    # Unit Prices (online prices for known products)
    price_lookup = {
        "ALAMYCIN 10": 213,
        "ALAMYCIN 20": 450,
        "OPTICLOX": 1100,
        "BENDAMEC": 198,
        "LEVAFAS XTRA": 150,
        "LEVAFAS DIAMOND": 200,
        "LEVAFAS DRENCH": 180,
        "ALBAFAS 2.5": 120,
        "ALBAFAS 10": 180,
        "DUOTECH": 250,
        "NOROTRAZ 12.5": 300
    }

    def get_price(name):
        for key, price in price_lookup.items():
            if key.upper() in name.upper():
                return price
        return 0

    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                # Get description column
                desc_key = column_map.get('description', 'DESCRIPTION')
                description = str(row.get(desc_key, "")).strip()
                
                # Get unnamed:3 column (if exists)
                unnamed_3 = ""
                if 'unnamed: 3' in column_map:
                    unnamed_3 = str(row.get(column_map['unnamed: 3'], "")).strip()
                
                # Combine into product name
                product_name = f"{description} {unnamed_3}".strip()
                
                if not product_name or product_name == "":
                    continue

                # Get quantity column
                qty_key = column_map.get('quantity', 'QUANTITY')
                current_stock = int(pd.to_numeric(row.get(qty_key), errors="coerce") or 0)
                
                # Generate SKU
                sku = (product_name[:3].upper() if len(product_name) >= 3 else product_name.upper()).ljust(3, "X") + str(index+1).zfill(3)
                
                # Get price
                unit_price = get_price(product_name)

                # Get or create category
                category_name = description.strip()
                if not category_name:
                    category_name = "Uncategorized"
                
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={
                        'description': f'Category for {category_name}',
                        'is_active': True
                    }
                )

                # Try to find existing product or create new one
                product, created = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "name": product_name,
                        "price": unit_price,
                        "stock_quantity": current_stock,
                        "min_stock_level": 10,
                        "category": category,
                    },
                )

                if not created:
                    # Update existing product
                    product.name = product_name
                    product.price = unit_price
                    product.stock_quantity = current_stock
                    product.category = category
                    product.save()

                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    movement_type="purchase",
                    quantity=current_stock,
                    previous_stock=0,
                    new_stock=current_stock,
                    reference_number=f'IMPORT_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                    notes=f"Bulk import from Excel - Row {index + 2}",
                    user=user,
                )

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 2}: {str(e)}")
                continue

    return success_count, error_count, errors


def process_standard_format(df, column_map, user):
    """Process standard Excel format."""
    success_count = 0
    error_count = 0
    errors = []

    # Map required columns
    required_columns = {
        'product name': column_map.get('product name'),
        'sku': column_map.get('sku'),
        'current stock': column_map.get('current stock'),
        'unit price': column_map.get('unit price')
    }
    
    # Check for missing columns
    missing_columns = [key for key, value in required_columns.items() if not value]
    if missing_columns:
        errors.append(f'Missing required columns: {", ".join(missing_columns)}')
        return 0, 1, errors

    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                product_name = str(row[required_columns['product name']]).strip()
                sku = str(row[required_columns['sku']]).strip()
                current_stock = int(pd.to_numeric(row[required_columns['current stock']], errors="coerce") or 0)
                unit_price = Decimal(str(row[required_columns['unit price']]))

                if not product_name or not sku:
                    error_count += 1
                    errors.append(f"Row {index + 2}: Missing product name or SKU")
                    continue

                # Get category if available
                category = None
                if 'category' in column_map:
                    category_name = str(row[column_map['category']]).strip()
                    if category_name:
                        category, _ = Category.objects.get_or_create(
                            name=category_name,
                            defaults={
                                'description': f'Category for {category_name}',
                                'is_active': True
                            }
                        )

                # Try to find existing product or create new one
                product, created = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "name": product_name,
                        "price": unit_price,
                        "stock_quantity": current_stock,
                        "min_stock_level": 10,
                        "category": category,
                    },
                )

                if not created:
                    # Update existing product
                    product.name = product_name
                    product.price = unit_price
                    product.stock_quantity = current_stock
                    if category:
                        product.category = category
                    product.save()

                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    movement_type="purchase",
                    quantity=current_stock,
                    previous_stock=0,
                    new_stock=current_stock,
                    reference_number=f'IMPORT_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                    notes=f"Bulk import from Excel - Row {index + 2}",
                    user=user,
                )

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 2}: {str(e)}")
                continue

    return success_count, error_count, errors


def auto_detect_format(df, column_map, user):
    """Auto-detect Excel format and process accordingly."""
    success_count = 0
    error_count = 0
    errors = []

    # Try to identify columns by content
    detected_columns = {}
    
    for col_name, col_data in df.items():
        col_lower = col_name.lower()
        
        # Check if column contains numeric data (likely quantities or prices)
        if col_data.dtype in ['int64', 'float64'] or col_data.astype(str).str.match(r'^\d+\.?\d*$').any():
            if col_data.max() > 1000:  # Likely prices
                detected_columns['unit_price'] = col_name
            else:  # Likely quantities
                detected_columns['current_stock'] = col_name
        
        # Check for text columns that might be product names or SKUs
        elif col_data.dtype == 'object':
            # Check if column contains alphanumeric codes (likely SKUs)
            if col_data.astype(str).str.match(r'^[A-Z0-9]{3,10}$').any():
                detected_columns['sku'] = col_name
            else:
                # Assume it's product name
                detected_columns['product_name'] = col_name

    # If we can't detect enough columns, return error
    if len(detected_columns) < 3:
        errors.append("Could not auto-detect column format. Please ensure your Excel file has clear column headers.")
        return 0, 1, errors

    with transaction.atomic():
        for index, row in df.iterrows():
            try:
                product_name = str(row.get(detected_columns.get('product_name', ''), '')).strip()
                sku = str(row.get(detected_columns.get('sku', ''), '')).strip()
                current_stock = int(pd.to_numeric(row.get(detected_columns.get('current_stock', 0), 0), errors="coerce") or 0)
                unit_price = Decimal(str(row.get(detected_columns.get('unit_price', 0), 0)))

                if not product_name:
                    continue

                # Generate SKU if not provided
                if not sku:
                    sku = (product_name[:3].upper() if len(product_name) >= 3 else product_name.upper()).ljust(3, "X") + str(index+1).zfill(3)

                # Create or update product
                product, created = Product.objects.get_or_create(
                    sku=sku,
                    defaults={
                        "name": product_name,
                        "price": unit_price,
                        "stock_quantity": current_stock,
                        "min_stock_level": 10,
                    },
                )

                if not created:
                    product.name = product_name
                    product.price = unit_price
                    product.stock_quantity = current_stock
                    product.save()

                # Create stock movement record
                StockMovement.objects.create(
                    product=product,
                    movement_type="purchase",
                    quantity=current_stock,
                    previous_stock=0,
                    new_stock=current_stock,
                    reference_number=f'IMPORT_{timezone.now().strftime("%Y%m%d_%H%M%S")}',
                    notes=f"Bulk import from Excel - Row {index + 2}",
                    user=user,
                )

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Row {index + 2}: {str(e)}")
                continue

    return success_count, error_count, errors


@login_required
def export_stock_movements(request):
    """Export stock movements to Excel."""
    try:
        # Get filtered movements
        movements = StockMovement.objects.select_related("product", "user").order_by("-created_at")

        # Apply filters if provided
        product_filter = request.GET.get("product")
        movement_type = request.GET.get("type")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        if product_filter:
            movements = movements.filter(product__name__icontains=product_filter)
        if movement_type:
            movements = movements.filter(movement_type=movement_type)
        if date_from:
            movements = movements.filter(created_at__date__gte=date_from)
        if date_to:
            movements = movements.filter(created_at__date__lte=date_to)

        # Create DataFrame
        data = []
        for movement in movements:
            data.append(
                {
                    "Date": movement.created_at.strftime("%Y-%m-%d %H:%M"),
                    "Product Name": movement.product.name,
                    "SKU": movement.product.sku,
                    "Movement Type": movement.movement_type.title(),
                    "Quantity": movement.quantity,
                    "Reference": movement.reference_number,
                    "User": movement.user.username,
                    "Notes": movement.notes or "",
                }
            )

        df = pd.DataFrame(data)

        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Stock Movements", index=False)

            # Get the worksheet
            worksheet = writer.sheets["Stock Movements"]

            # Style the header row
            header_font = Font(bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")

            for cell in worksheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")

            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except (ValueError, TypeError):
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        # Create response
        response = HttpResponse(
            output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="stock_movements_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
        )

        return response

    except Exception as e:
        messages.error(request, f"Error exporting stock movements: {str(e)}")
        return redirect("inventory:stock_movements")


@login_required
def stock_alerts(request):
    """View stock alerts and low stock products."""
    low_stock_products = Product.objects.filter(stock_quantity__lte=F("min_stock_level")).order_by("stock_quantity")
    out_of_stock = Product.objects.filter(stock_quantity=0)

    # Get active stock alerts
    active_alerts = (
        StockAlert.objects.filter(status="active").select_related("product").order_by("-priority", "-created_at")
    )

    context = {
        "low_stock_products": low_stock_products,
        "out_of_stock": out_of_stock,
        "active_alerts": active_alerts,
    }

    return render(request, "inventory/stock_alerts.html", context)


@login_required
def stock_alerts_json(request):
    """Return stock alerts as JSON for AJAX requests."""
    from django.http import JsonResponse

    alerts = (
        StockAlert.objects.filter(status="active")
        .select_related("product", "product__category")
        .order_by("-priority", "-created_at")[:20]
    )

    alerts_data = []
    for alert in alerts:
        alerts_data.append(
            {
                "id": alert.alert_id,
                "type": alert.get_alert_type_display(),
                "priority": alert.get_priority_display(),
                "status": alert.get_status_display(),
                "current_value": alert.current_value,
                "threshold_value": alert.threshold_value,
                "message": alert.message,
                "created_at": alert.created_at.strftime("%Y-%m-%d %H:%M"),
                "product": {
                    "id": alert.product.id,
                    "name": alert.product.name,
                    "sku": alert.product.sku or "N/A",
                    "category": alert.product.category.name if alert.product.category else "Uncategorized",
                    "price": str(alert.product.price),
                },
            }
        )

    return JsonResponse({"alerts": alerts_data, "count": len(alerts_data), "timestamp": timezone.now().isoformat()})


@login_required
def acknowledge_alert(request, alert_id):
    """Acknowledge a stock alert."""
    from django.http import JsonResponse

    try:
        alert = StockAlert.objects.get(alert_id=alert_id)
        alert.acknowledge(request.user)

        return JsonResponse({"success": True, "message": f"Alert for {alert.product.name} has been acknowledged"})
    except StockAlert.DoesNotExist:
        return JsonResponse({"success": False, "message": "Alert not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error acknowledging alert: {str(e)}"}, status=500)


@login_required
def resolve_alert(request, alert_id):
    """Resolve a stock alert."""
    from django.http import JsonResponse

    try:
        alert = StockAlert.objects.get(alert_id=alert_id)
        alert.resolve(request.user)

        return JsonResponse({"success": True, "message": f"Alert for {alert.product.name} has been resolved"})
    except StockAlert.DoesNotExist:
        return JsonResponse({"success": False, "message": "Alert not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error resolving alert: {str(e)}"}, status=500)


@login_required
def purchase_orders(request):
    """View and manage purchase orders."""
    orders = PurchaseOrder.objects.select_related("supplier").order_by("-created_at")

    context = {
        "orders": orders,
    }

    return render(request, "inventory/purchase_orders.html", context)


@login_required
def stock_management(request):
    """Stock management page with inline editing for prices and quantities."""
    if request.method == "POST":
        # Handle inline updates
        product_id = request.POST.get("product_id")
        field = request.POST.get("field")
        value = request.POST.get("value")
        
        if product_id and field and value:
            try:
                product = Product.objects.get(id=product_id)
                
                if field == "price":
                    # Update price
                    new_price = Decimal(value)
                    old_price = product.price
                    product.price = new_price
                    product.save()
                    
                    # Note: Price changes don't create stock movements
                    # Stock movements track quantity changes only
                    # Price changes are tracked in product model history
                    
                    messages.success(request, f"Price updated for {product.name}")
                    
                elif field == "stock_quantity":
                    # Update stock quantity
                    new_quantity = int(value)
                    old_quantity = product.stock_quantity
                    product.stock_quantity = new_quantity
                    product.save()
                    
                    # Create stock movement
                    quantity_diff = new_quantity - old_quantity
                    if quantity_diff > 0:
                        movement_type = StockMovement.MovementType.PURCHASE
                    elif quantity_diff < 0:
                        movement_type = StockMovement.MovementType.ADJUSTMENT
                    else:
                        movement_type = StockMovement.MovementType.ADJUSTMENT
                    
                    StockMovement.objects.create(
                        product=product,
                        movement_type=movement_type,
                        quantity=quantity_diff,
                        previous_stock=old_quantity,
                        new_stock=new_quantity,
                        reference_type='Manual Adjustment',
                        notes=f"Stock quantity updated from {old_quantity} to {new_quantity}",
                        user=request.user
                    )
                    
                    messages.success(request, f"Stock quantity updated for {product.name}")
                    
                elif field == "min_stock_level":
                    # Update minimum stock level
                    new_min = int(value)
                    product.min_stock_level = new_min
                    product.save()
                    messages.success(request, f"Minimum stock level updated for {product.name}")
                    
                return JsonResponse({"success": True, "message": "Updated successfully"})
                
            except (Product.DoesNotExist, ValueError, TypeError) as e:
                return JsonResponse({"success": False, "message": str(e)})
    
    # Get products with pagination
    products = Product.objects.select_related('category').order_by('name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        products = products.filter(category_id=category_filter)
    
    # Filter by stock status
    stock_filter = request.GET.get('stock_status', '')
    if stock_filter == 'low':
        products = products.filter(stock_quantity__lte=F('min_stock_level'))
    elif stock_filter == 'out':
        products = products.filter(stock_quantity=0)
    elif stock_filter == 'in_stock':
        products = products.filter(stock_quantity__gt=F('min_stock_level'))
    
    # Pagination
    paginator = Paginator(products, 20)  # 20 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = Category.objects.all().order_by('name')
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search': search,
        'category_filter': category_filter,
        'stock_filter': stock_filter,
    }
    
    return render(request, "inventory/stock_management.html", context)


# Document Generation Views for Inventory

@login_required
def inventory_documents(request):
    """List all documents related to inventory."""
    if not DOCUMENTS_AVAILABLE:
        messages.warning(request, "Document system is not available.")
        return redirect('inventory:dashboard')
    
    documents = Document.objects.filter(
        document_type__in=['receipt', 'quotation', 'invoice']
    ).order_by('-created_at')
    
    # Filtering
    document_type = request.GET.get('type')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if document_type:
        documents = documents.filter(document_type=document_type)
    if status:
        documents = documents.filter(status=status)
    if search:
        documents = documents.filter(
            Q(document_number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(title__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'document_types': DocumentTemplate.DOCUMENT_TYPES if DOCUMENTS_AVAILABLE else [],
        'status_choices': Document.DOCUMENT_STATUS if DOCUMENTS_AVAILABLE else [],
        'filters': {
            'type': document_type,
            'status': status,
            'search': search,
        },
        'documents_available': DOCUMENTS_AVAILABLE,
    }
    
    return render(request, "inventory/documents.html", context)


@login_required
def generate_receipt_from_stock(request):
    """Generate receipt from stock movement."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:documents')
    
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '')
        customer_email = request.POST.get('customer_email', '')
        customer_phone = request.POST.get('customer_phone', '')
        payment_method = request.POST.get('payment_method', '')
        tax_rate = float(request.POST.get('tax_rate', 0))
        discount_amount = float(request.POST.get('discount_amount', 0))
        receipt_notes = request.POST.get('receipt_notes', '')
        
        try:
            # Get template
            template = DocumentTemplate.objects.filter(document_type='receipt', is_active=True).first()
            if not template:
                template = DocumentTemplate.objects.create(
                    name='Standard Receipt',
                    document_type='receipt',
                    template_html='<h1>Receipt</h1>',
                    is_active=True
                )
            
            # Create receipt document
            receipt = Document.objects.create(
                document_number=f"RCP-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                document_type='receipt',
                template=template,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                created_by=request.user,
                issue_date=timezone.now().date(),
                notes=receipt_notes
            )
            
            # Add items to receipt
            subtotal = Decimal('0.00')
            
            # Handle items from form
            i = 0
            while f'items[{i}][id]' in request.POST:
                item_id = request.POST.get(f'items[{i}][id]')
                quantity = int(request.POST.get(f'items[{i}][quantity]', 1))
                
                if item_id:
                    product = Product.objects.get(id=item_id)
                    unit_price = product.price
                    total_price = unit_price * Decimal(str(quantity))
                    subtotal += total_price
                    
                    DocumentItem.objects.create(
                        document=receipt,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                i += 1
            
            # Calculate totals
            tax_amount = (subtotal * Decimal(str(tax_rate))) / Decimal('100')
            total_amount = subtotal + tax_amount - Decimal(str(discount_amount))
            
            receipt.subtotal = subtotal
            receipt.tax_amount = tax_amount
            receipt.discount_amount = discount_amount
            receipt.total_amount = total_amount
            receipt.save()
            
            messages.success(request, f"Receipt {receipt.document_number} created successfully.")
            return redirect('inventory:view_document', pk=receipt.id)
            
        except Exception as e:
            messages.error(request, f"Error creating receipt: {str(e)}")
    
    # For GET requests, just render the template with JavaScript handling
    context = {
        'current_date': timezone.now(),
        'documents_available': DOCUMENTS_AVAILABLE,
    }
    
    return render(request, "inventory/generate_receipt.html", context)


@login_required
def generate_quotation_from_products(request):
    """Generate quotation from selected products."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:documents')
    
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '')
        customer_email = request.POST.get('customer_email', '')
        customer_phone = request.POST.get('customer_phone', '')
        customer_address = request.POST.get('customer_address', '')
        validity_days = int(request.POST.get('validity_days', 30))
        tax_rate = float(request.POST.get('tax_rate', 0))
        discount_percentage = float(request.POST.get('discount_percentage', 0))
        terms_conditions = request.POST.get('terms_conditions', '')
        
        try:
            # Get template
            template = DocumentTemplate.objects.filter(document_type='quotation', is_active=True).first()
            if not template:
                template = DocumentTemplate.objects.create(
                    name='Standard Quotation',
                    document_type='quotation',
                    template_html='<h1>Quotation</h1>',
                    is_active=True
                )
            
            # Create quotation document
            quotation = Document.objects.create(
                document_number=f"QTN-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                document_type='quotation',
                template=template,
                title=f'Quotation for {customer_name}',
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_address=customer_address,
                created_by=request.user,
                issue_date=timezone.now().date(),
                due_date=timezone.now().date() + timezone.timedelta(days=validity_days),
                notes=terms_conditions
            )
            
            # Add products to quotation
            subtotal = Decimal('0.00')
            
            # Handle products from form
            i = 0
            while f'products[{i}][id]' in request.POST:
                product_id = request.POST.get(f'products[{i}][id]')
                quantity = int(request.POST.get(f'products[{i}][quantity]', 1))
                
                if product_id:
                    product = Product.objects.get(id=product_id)
                    unit_price = product.price
                    total_price = unit_price * Decimal(str(quantity))
                    subtotal += total_price
                    
                    DocumentItem.objects.create(
                        document=quotation,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                i += 1
            
            # Calculate totals
            tax_amount = (subtotal * Decimal(str(tax_rate))) / Decimal('100')
            discount_amount = (subtotal * Decimal(str(discount_percentage))) / Decimal('100')
            total_amount = subtotal + tax_amount - discount_amount
            
            quotation.subtotal = subtotal
            quotation.tax_amount = tax_amount
            quotation.discount_amount = discount_amount
            quotation.total_amount = total_amount
            quotation.save()
            
            messages.success(request, f"Quotation {quotation.document_number} created successfully.")
            return redirect('inventory:view_document', pk=quotation.id)
            
        except Exception as e:
            messages.error(request, f"Error creating quotation: {str(e)}")
    
    # Get cart items for the current user
    from orders.models import Cart, CartItem
    from orders.views import get_or_create_cart
    
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    context = {
        'current_date': timezone.now(),
        'documents_available': DOCUMENTS_AVAILABLE,
        'cart_items': cart_items,
        'cart': cart,
    }
    
    return render(request, "inventory/generate_quotation.html", context)


@login_required
def view_document(request, pk):
    """View document details."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:dashboard')
    
    document = get_object_or_404(Document, pk=pk)
    
    context = {
        'document': document,
        'documents_available': DOCUMENTS_AVAILABLE,
    }
    
    return render(request, "inventory/document_detail.html", context)


@login_required
def download_document_pdf(request, pk):
    """Download document as PDF."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:view_document', pk=pk)
    
    document = get_object_or_404(Document, pk=pk)
    
    try:
        if document.document_type == 'receipt':
            pdf_content = generate_receipt_pdf(document, request)
        elif document.document_type == 'quotation':
            pdf_content = generate_quotation_pdf(document, request)
        elif document.document_type == 'invoice':
            pdf_content = generate_invoice_pdf(document, request)
        elif document.document_type == 'purchase_order':
            pdf_content = generate_purchase_order_pdf(document, request)
        else:
            messages.error(request, "Unsupported document type.")
            return redirect('inventory:view_document', pk=pk)
        
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{document.document_number}.pdf"'
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating PDF: {str(e)}")
        return redirect('inventory:view_document', pk=pk)


@login_required
def email_document(request, pk):
    """Email document to customer."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:view_document', pk=pk)
    
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        email_address = request.POST.get('email_address', document.customer_email)
        subject = request.POST.get('subject', f'{document.document_type.title()} - {document.document_number}')
        message = request.POST.get('message', '')
        
        try:
            send_document_email(document, email_address, subject, message, request)
            messages.success(request, f"Document sent to {email_address}")
        except Exception as e:
            messages.error(request, f"Error sending email: {str(e)}")
    
    context = {
        'document': document,
        'documents_available': DOCUMENTS_AVAILABLE,
    }
    
    return render(request, "inventory/email_document.html", context)


@login_required
def print_document_view(request, pk):
    """Print document."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:view_document', pk=pk)
    
    document = get_object_or_404(Document, pk=pk)
    
    try:
        print_document(document, request)
        messages.success(request, "Document sent to printer")
    except Exception as e:
        messages.error(request, f"Error printing document: {str(e)}")
    
    return redirect('inventory:view_document', pk=pk)


@login_required
def generate_invoice(request):
    """Generate invoice from selected products."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:documents')
    
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '')
        customer_email = request.POST.get('customer_email', '')
        customer_phone = request.POST.get('customer_phone', '')
        customer_address = request.POST.get('customer_address', '')
        due_date = request.POST.get('due_date', '')
        payment_terms = request.POST.get('payment_terms', '')
        tax_rate = float(request.POST.get('tax_rate', 0))
        discount_percentage = float(request.POST.get('discount_percentage', 0))
        notes = request.POST.get('notes', '')
        
        try:
            # Get template
            template = DocumentTemplate.objects.filter(document_type='invoice', is_active=True).first()
            if not template:
                template = DocumentTemplate.objects.create(
                    name='Standard Invoice',
                    document_type='invoice',
                    template_html='<h1>Invoice</h1>',
                    is_active=True
                )
            
            # Create invoice document
            invoice = Document.objects.create(
                document_number=f"INV-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                document_type='invoice',
                template=template,
                title=f'Invoice for {customer_name}',
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                customer_address=customer_address,
                created_by=request.user,
                issue_date=timezone.now().date(),
                due_date=due_date if due_date else None,
                notes=notes
            )
            
            subtotal = Decimal('0.00')
            
            # Handle products from form
            i = 0
            while f'products[{i}][id]' in request.POST:
                product_id = request.POST.get(f'products[{i}][id]')
                quantity = int(request.POST.get(f'products[{i}][quantity]', 1))
                
                if product_id:
                    product = Product.objects.get(id=product_id)
                    unit_price = product.price
                    total_price = unit_price * Decimal(str(quantity))
                    subtotal += total_price
                    
                    DocumentItem.objects.create(
                        document=invoice,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                i += 1
            
            # Calculate totals
            tax_amount = (subtotal * Decimal(str(tax_rate))) / Decimal('100')
            discount_amount = (subtotal * Decimal(str(discount_percentage))) / Decimal('100')
            total_amount = subtotal + tax_amount - discount_amount
            
            invoice.subtotal = subtotal
            invoice.tax_amount = tax_amount
            invoice.discount_amount = discount_amount
            invoice.total_amount = total_amount
            invoice.save()
            
            # Clear the cart after successful invoice generation
            cart.items.all().delete()
            
            messages.success(request, f"Invoice {invoice.document_number} created successfully.")
            return redirect('inventory:view_document', pk=invoice.id)
            
        except Exception as e:
            messages.error(request, f"Error creating invoice: {str(e)}")
    
    # Get cart items for the current user
    from orders.models import Cart, CartItem
    from orders.views import get_or_create_cart
    
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    context = {
        'current_date': timezone.now(),
        'documents_available': DOCUMENTS_AVAILABLE,
        'cart_items': cart_items,
        'cart': cart,
    }
    
    return render(request, "inventory/generate_invoice.html", context)


@login_required
def generate_purchase_order(request):
    """Generate purchase order."""
    if not DOCUMENTS_AVAILABLE:
        messages.error(request, "Document system is not available.")
        return redirect('inventory:documents')
    
    if request.method == 'POST':
        supplier_name = request.POST.get('supplier_name', '')
        supplier_email = request.POST.get('supplier_email', '')
        supplier_phone = request.POST.get('supplier_phone', '')
        supplier_address = request.POST.get('supplier_address', '')
        delivery_date = request.POST.get('delivery_date', '')
        payment_terms = request.POST.get('payment_terms', '')
        notes = request.POST.get('notes', '')
        
        try:
            # Get template
            template = DocumentTemplate.objects.filter(document_type='purchase_order', is_active=True).first()
            if not template:
                template = DocumentTemplate.objects.create(
                    name='Standard Purchase Order',
                    document_type='purchase_order',
                    template_html='<h1>Purchase Order</h1>',
                    is_active=True
                )
            
            # Create purchase order document
            po = Document.objects.create(
                document_number=f"PO-{timezone.now().strftime('%Y%m%d%H%M%S')}",
                document_type='purchase_order',
                template=template,
                title=f'Purchase Order for {supplier_name}',
                customer_name=supplier_name,  # Using customer_name field for supplier
                customer_email=supplier_email,
                customer_phone=supplier_phone,
                customer_address=supplier_address,
                created_by=request.user,
                issue_date=timezone.now().date(),
                due_date=delivery_date if delivery_date else None,
                notes=notes
            )
            
            subtotal = Decimal('0.00')
            
            # Handle products from form
            i = 0
            while f'products[{i}][id]' in request.POST:
                product_id = request.POST.get(f'products[{i}][id]')
                quantity = int(request.POST.get(f'products[{i}][quantity]', 1))
                
                if product_id:
                    product = Product.objects.get(id=product_id)
                    unit_price = product.price
                    total_price = unit_price * Decimal(str(quantity))
                    subtotal += total_price
                    
                    DocumentItem.objects.create(
                        document=po,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price
                    )
                i += 1
            
            po.subtotal = subtotal
            po.total_amount = subtotal
            po.save()
            
            messages.success(request, f"Purchase Order {po.document_number} created successfully.")
            return redirect('inventory:view_document', pk=po.id)
            
        except Exception as e:
            messages.error(request, f"Error creating purchase order: {str(e)}")
    
    context = {
        'current_date': timezone.now(),
        'documents_available': DOCUMENTS_AVAILABLE,
    }
    
    return render(request, "inventory/generate_purchase_order.html", context)




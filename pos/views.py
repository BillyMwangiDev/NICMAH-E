"""
Enhanced POS views with barcode scanning, tax calculation, and discount system.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse

from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from decimal import Decimal, InvalidOperation
import json
import uuid

from .models import POSSession, POSSale, POSSaleItem, Receipt, Barcode, TaxRate, Discount, OfflineTransaction
from catalog.models import Product


@login_required
def pos_dashboard(request):
    """Enhanced POS dashboard with real-time metrics and session management."""

    # Get or create active session
    active_session = POSSession.objects.filter(cashier=request.user, status="open").first()

    if not active_session:
        active_session = POSSession.objects.create(
            cashier=request.user, seller=request.user if request.user.role == "seller" else None
        )

    # Get today's sales data
    today = timezone.now().date()
    today_sales = POSSale.objects.filter(session=active_session, created_at__date=today, status="completed")

    # Calculate metrics
    today_total = today_sales.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    today_transactions = today_sales.count()
    today_tax = today_sales.aggregate(tax=Sum("tax_amount"))["tax"] or Decimal("0.00")
    today_discounts = today_sales.aggregate(discounts=Sum("discount_amount"))["discounts"] or Decimal("0.00")

    # Get available products for quick search
    products = Product.objects.filter(is_active=True, stock_quantity__gt=0)[:10]

    # Get available tax rates
    tax_rates = TaxRate.objects.filter(is_active=True)

    # Get available discounts
    active_discounts = Discount.objects.filter(is_active=True).filter(
        start_date__lte=timezone.now(), end_date__gte=timezone.now()
    )

    # Get recent sales for the session
    recent_sales = POSSale.objects.filter(
        session=active_session
    ).select_related("cashier", "seller").prefetch_related("items").order_by("-created_at")[:10]

    context = {
        "active_session": active_session,
        "today_total": today_total,
        "today_transactions": today_transactions,
        "today_tax": today_tax,
        "today_discounts": today_discounts,
        "products": products,
        "tax_rates": tax_rates,
        "active_discounts": active_discounts,
        "session_summary": active_session.get_session_summary() if active_session else None,
        "recent_sales": recent_sales,
    }

    return render(request, "pos/dashboard.html", context)


@login_required
def pos_sale_create(request):
    """Create a new POS sale with enhanced features."""

    if request.method == "POST":
        try:
            # Parse JSON data
            try:
                sale_data = json.loads(request.body)
            except json.JSONDecodeError as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Invalid JSON in sale creation: {e}")
                return JsonResponse({"success": False, "error": f"Invalid JSON data: {str(e)}"}, status=400)
            
            # Validate required fields
            if not sale_data.get("items") or len(sale_data.get("items", [])) == 0:
                return JsonResponse({"success": False, "error": "No items in sale"}, status=400)
            
            with transaction.atomic():
                # Get active session
                try:
                    active_session = POSSession.objects.get(cashier=request.user, status="open")
                except POSSession.DoesNotExist:
                    return JsonResponse({"success": False, "error": "No active POS session found. Please start a session first."}, status=400)
                
                # Import settings for auto-print check
                from core.models import SiteSettings
                settings = SiteSettings.objects.first()

                # Get tax rate if provided
                tax_rate = None
                if sale_data.get("tax_rate_id"):
                    try:
                        tax_rate = TaxRate.objects.get(id=sale_data.get("tax_rate_id"))
                    except TaxRate.DoesNotExist:
                        pass

                sale = POSSale.objects.create(
                    session=active_session,
                    cashier=request.user,
                    seller=active_session.seller or request.user,
                    payment_method=sale_data.get("payment_method", "cash"),
                    tax_rate=tax_rate,
                    notes=sale_data.get("notes", ""),
                )

                # Add items
                total_amount = Decimal("0.00")
                for item_data in sale_data.get("items", []):
                    # Validate item data
                    if not item_data.get("product_id"):
                        return JsonResponse({"success": False, "error": "Missing product_id in item"}, status=400)
                    if not item_data.get("quantity"):
                        return JsonResponse({"success": False, "error": "Missing quantity in item"}, status=400)
                    if not item_data.get("unit_price"):
                        return JsonResponse({"success": False, "error": "Missing unit_price in item"}, status=400)
                    
                    try:
                        product = Product.objects.get(id=item_data["product_id"])
                    except Product.DoesNotExist:
                        return JsonResponse({"success": False, "error": f"Product with ID {item_data['product_id']} not found"}, status=400)
                    
                    try:
                        quantity = int(item_data["quantity"])
                        if quantity <= 0:
                            return JsonResponse({"success": False, "error": f"Quantity must be greater than 0 for {product.name}"}, status=400)
                    except (ValueError, TypeError):
                        return JsonResponse({"success": False, "error": f"Invalid quantity for {product.name}"}, status=400)
                    
                    try:
                        unit_price = Decimal(str(item_data["unit_price"]))
                        if unit_price < 0:
                            return JsonResponse({"success": False, "error": f"Unit price cannot be negative for {product.name}"}, status=400)
                    except (ValueError, TypeError, InvalidOperation):
                        return JsonResponse({"success": False, "error": f"Invalid unit_price for {product.name}"}, status=400)

                    # Check stock
                    if product.stock_quantity < quantity:
                        return JsonResponse({"success": False, "error": f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {quantity}"}, status=400)

                    # Create sale item
                    sale_item = POSSaleItem.objects.create(
                        sale=sale, product=product, quantity=quantity, unit_price=unit_price
                    )

                    # Apply item discounts if any
                    for discount_id in item_data.get("discounts", []):
                        try:
                            # Convert to int if it's a string
                            discount_id = int(discount_id) if discount_id else None
                            if discount_id:
                                discount = Discount.objects.get(id=discount_id)
                                if discount.is_valid():
                                    sale_item.apply_item_discount(discount)
                        except (Discount.DoesNotExist, ValueError, TypeError) as e:
                            # Log the error for debugging
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.warning(f"Discount with ID {discount_id} not found or invalid for sale item: {e}")

                    # Note: Stock is automatically deducted in POSSaleItem.save() method
                    # No need to manually update stock here to avoid double deduction

                    total_amount += sale_item.total_price

                # Apply sale-level discounts
                for discount_id in sale_data.get("sale_discounts", []):
                    try:
                        # Convert to int if it's a string
                        discount_id = int(discount_id) if discount_id else None
                        if discount_id:
                            discount = Discount.objects.get(id=discount_id)
                            if discount.is_valid():
                                sale.applied_discounts.add(discount)
                    except (Discount.DoesNotExist, ValueError, TypeError) as e:
                        # Log the error for debugging
                        logger.warning(f"Discount with ID {discount_id} not found or invalid: {e}")

                # Refresh sale from database to get updated items
                sale.refresh_from_db()
                
                # Save to recalculate totals (this triggers the save() method which recalculates)
                sale.save()

                # Calculate change
                amount_paid = Decimal(sale_data.get("amount_paid", "0.00"))
                sale.change_amount = amount_paid - sale.total_amount

                # Mark as completed (this will trigger the signal to create unified Sales record)
                sale.status = "completed"
                sale.payment_status = "paid"
                sale.save()  # Signal will create unified Sales record here

                # Generate receipt (receipt_number will be auto-generated using sale's receipt_number)
                receipt = Receipt.objects.create(
                    sale=sale,
                    content=f"Receipt for sale {sale.sale_number}",
                )
                
                # Auto-print receipt if enabled
                print_status = None
                if settings.printer_enabled and settings.auto_print_receipts:
                    try:
                        from .printer import ReceiptPrinter
                        from core.models import SiteSettings as PrinterSettings
                        
                        printer_settings = PrinterSettings.objects.first()
                        if printer_settings:
                            connection_params = {}
                            if printer_settings.printer_type == 'network':
                                connection_params = {
                                    'host': printer_settings.printer_host,
                                    'port': printer_settings.printer_port,
                                    'timeout': 5
                                }
                                printer_name = None
                            elif printer_settings.printer_type == 'serial':
                                connection_params = {
                                    'port': printer_settings.printer_serial_port,
                                    'baudrate': printer_settings.printer_baudrate,
                                    'timeout': 5
                                }
                                printer_name = None
                            else:
                                printer_name = printer_settings.printer_name
                            
                            printer = ReceiptPrinter(
                                printer_type=printer_settings.printer_type,
                                printer_name=printer_name,
                                connection_params=connection_params
                            )
                            printer.print_receipt(sale)
                            print_status = "sent"
                    except Exception as e:
                        logger.warning(f"Auto-print failed: {str(e)}")
                        print_status = "failed"

                return JsonResponse(
                    {
                        "success": True,
                        "sale_id": sale.id,
                        "sale_number": sale.sale_number,
                        "total_amount": str(sale.total_amount),
                        "receipt_number": receipt.receipt_number,
                        "print_status": print_status,
                    }
                )

        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            error_traceback = traceback.format_exc()
            logger.error(f"Error creating POS sale: {str(e)}\n{error_traceback}")
            # Return more detailed error in development
            error_msg = str(e)
            if hasattr(e, '__cause__') and e.__cause__:
                error_msg += f" (Cause: {str(e.__cause__)})"
            return JsonResponse({"success": False, "error": f"Error creating sale: {error_msg}"}, status=400)

    # GET request - show sale form
    active_session = get_object_or_404(POSSession, cashier=request.user, status="open")

    products = Product.objects.filter(is_active=True, stock_quantity__gt=0)
    tax_rates = TaxRate.objects.filter(is_active=True)
    active_discounts = Discount.objects.filter(is_active=True).filter(
        start_date__lte=timezone.now(), end_date__gte=timezone.now()
    )

    context = {
        "active_session": active_session,
        "products": products,
        "tax_rates": tax_rates,
        "active_discounts": active_discounts,
    }

    return render(request, "pos/sale_create.html", context)


@login_required
def pos_sale_detail(request, sale_id):
    """View detailed information about a POS sale."""

    sale = get_object_or_404(POSSale, id=sale_id)

    # Check permissions
    if not (
        request.user.is_superuser
        or request.user.role in ["admin", "manager"]
        or sale.cashier == request.user
        or sale.seller == request.user
    ):
        messages.error(request, "You don't have permission to view this sale.")
        return redirect("pos:dashboard")

    context = {
        "sale": sale,
        "sale_summary": sale.get_sale_summary(),
        "items": sale.items.select_related('product', 'product__category').all(),
        "receipt": getattr(sale, "receipt", None),
    }

    return render(request, "pos/sale_detail.html", context)


@login_required
def pos_session_close(request, session_id):
    """Close a POS session."""

    session = get_object_or_404(POSSession, id=session_id)

    # Check permissions
    if session.cashier != request.user and not request.user.is_superuser:
        messages.error(request, "You can only close your own sessions.")
        return redirect("pos:dashboard")

    if request.method == "POST":
        closing_amount = request.POST.get("closing_amount", "0.00")
        try:
            session.closing_amount = Decimal(closing_amount)
            session.close_session()
            messages.success(request, f"Session {session.session_id} closed successfully.")
            return redirect("pos:dashboard")
        except Exception as e:
            messages.error(request, f"Error closing session: {str(e)}")

    context = {"session": session, "session_summary": session.get_session_summary()}

    return render(request, "pos/session_close.html", context)


@login_required
def pos_sales_list(request):
    """List all POS sales with filtering and pagination."""

    # Get sales based on user role
    if request.user.is_superuser or request.user.role in ["admin", "manager"]:
        sales = POSSale.objects.all()
    elif request.user.role == "seller":
        sales = POSSale.objects.filter(seller=request.user)
    else:
        sales = POSSale.objects.filter(cashier=request.user)

    # Apply filters
    status_filter = request.GET.get("status")
    payment_method_filter = request.GET.get("payment_method")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    if status_filter:
        sales = sales.filter(status=status_filter)
    if payment_method_filter:
        sales = sales.filter(payment_method=payment_method_filter)
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)

    # Pagination
    paginator = Paginator(sales.order_by("-created_at"), 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Calculate stats
    today = timezone.now().date()
    total_sales_result = sales.filter(status="completed").aggregate(total=Sum("total_amount"))
    total_sales_amount = total_sales_result.get("total") or Decimal("0.00")
    today_count = sales.filter(created_at__date=today).count()
    completed_count = sales.filter(status="completed").count()
    pending_count = sales.filter(status="pending").count()

    context = {
        "page_obj": page_obj,
        "total_sales": total_sales_amount,
        "today_count": today_count,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "filters": {
            "status": status_filter,
            "payment_method": payment_method_filter,
            "date_from": date_from,
            "date_to": date_to,
        },
    }

    return render(request, "pos/sales_list.html", context)


@login_required
def pos_barcode_scan(request):
    """API endpoint for barcode scanning."""

    if request.method == "POST":
        try:
            barcode_data = json.loads(request.body)
            barcode_value = barcode_data.get("barcode")

            if not barcode_value:
                return JsonResponse({"error": "Barcode value required"}, status=400)

            # Try to find product by barcode
            try:
                barcode_obj = Barcode.objects.get(barcode=barcode_value, is_active=True)
                product = barcode_obj.product
            except Barcode.DoesNotExist:
                # Try to find by SKU as fallback
                try:
                    product = Product.objects.get(sku=barcode_value, is_active=True)
                except Product.DoesNotExist:
                    return JsonResponse({"error": "Product not found"}, status=404)

            # Return product information
            return JsonResponse(
                {
                    "success": True,
                    "product": {
                        "id": product.id,
                        "name": product.name,
                        "price": str(product.price),
                        "stock_quantity": product.stock_quantity,
                        "sku": product.sku,
                        "category": product.category.name,
                        "image_url": product.main_image.url if product.main_image else None,
                    },
                }
            )

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def pos_product_search(request):
    """Search products for POS sale with autocomplete support and intelligent ranking."""

    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category")
    include_out_of_stock = request.GET.get("include_out_of_stock", "false").lower() == "true"

    # Base queryset - include out of stock if requested
    if include_out_of_stock:
        products = Product.objects.filter(is_active=True)
    else:
        products = Product.objects.filter(is_active=True, stock_quantity__gt=0)

    if query:
        # Enhanced search with better ranking
        # Priority 1: Exact name match
        exact_name = Q(name__iexact=query)
        # Priority 2: Name starts with query
        starts_with_name = Q(name__istartswith=query)
        # Priority 3: SKU exact match
        exact_sku = Q(sku__iexact=query)
        # Priority 4: SKU starts with query
        starts_with_sku = Q(sku__istartswith=query)
        # Priority 5: Barcode exact match
        exact_barcode = Q(barcodes__barcode__iexact=query, barcodes__is_active=True)
        # Priority 6: Name contains query
        contains_name = Q(name__icontains=query)
        # Priority 7: SKU contains query
        contains_sku = Q(sku__icontains=query)
        # Priority 8: Description contains query
        contains_description = Q(description__icontains=query)
        
        # Combine all search conditions
        products = products.filter(
            exact_name | starts_with_name | exact_sku | starts_with_sku | 
            exact_barcode | contains_name | contains_sku | contains_description
        ).distinct()
    else:
        # If no query, return empty results for autocomplete
        products = Product.objects.none()

    if category_id:
        products = products.filter(category_id=category_id)

    # Limit results for autocomplete
    limit = int(request.GET.get("limit", 10))
    
    # Get all matching products first
    all_products = list(products.select_related('category').prefetch_related('barcodes')[:limit * 2])
    
    # Rank products by relevance
    def calculate_relevance(product):
        score = 0
        query_lower = query.lower()
        name_lower = product.name.lower()
        sku_lower = product.sku.lower() if product.sku else ""
        
        # Exact matches get highest score
        if name_lower == query_lower:
            score += 1000
        elif name_lower.startswith(query_lower):
            score += 500
        elif query_lower in name_lower:
            score += 200
        
        # SKU matches
        if sku_lower == query_lower:
            score += 800
        elif sku_lower.startswith(query_lower):
            score += 400
        elif query_lower in sku_lower:
            score += 150
        
        # Barcode exact match
        if any(b.barcode.lower() == query_lower for b in product.barcodes.filter(is_active=True)):
            score += 900
        
        # Stock status bonus (in stock products ranked higher)
        if product.stock_quantity > 10:
            score += 100
        elif product.stock_quantity > 0:
            score += 50
        
        return score
    
    # Sort by relevance score (descending), then by stock quantity, then by name
    all_products.sort(key=lambda p: (-calculate_relevance(p), -p.stock_quantity, p.name))
    products = all_products[:limit]

    results = []
    for product in products:
        # Determine stock status
        if product.stock_quantity > 10:
            stock_status = "in_stock"
            stock_label = f"In Stock ({product.stock_quantity})"
        elif product.stock_quantity > 0:
            stock_status = "low_stock"
            stock_label = f"Low Stock ({product.stock_quantity})"
        else:
            stock_status = "out_of_stock"
            stock_label = "Out of Stock"
        
        results.append(
            {
                "id": product.id,
                "name": product.name,
                "price": str(product.price),
                "stock_quantity": product.stock_quantity,
                "stock_status": stock_status,
                "stock_label": stock_label,
                "sku": product.sku,
                "category": product.category.name if product.category else "Uncategorized",
                "image_url": product.main_image.url if product.main_image else None,
                "barcodes": [b.barcode for b in product.barcodes.filter(is_active=True)],
            }
        )

    return JsonResponse({"products": results})


@login_required
def pos_discount_apply(request):
    """Apply discount to sale or sale item."""

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            discount_id = data.get("discount_id")
            sale_id = data.get("sale_id")
            item_id = data.get("item_id")  # Optional, for item-level discounts

            discount = get_object_or_404(Discount, id=discount_id)

            if not discount.is_valid():
                return JsonResponse({"error": "Discount is not valid"}, status=400)

            if item_id:
                # Apply to specific item
                item = get_object_or_404(POSSaleItem, id=item_id)
                success = item.apply_item_discount(discount)
            else:
                # Apply to entire sale
                sale = get_object_or_404(POSSale, id=sale_id)
                success = sale.apply_discount(discount)

            if success:
                return JsonResponse(
                    {"success": True, "discount_amount": str(discount.calculate_discount(Decimal("0.00")))}
                )
            else:
                return JsonResponse({"error": "Failed to apply discount"}, status=400)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def pos_receipt_download(request, sale_id):
    """Download receipt as PDF."""

    sale = get_object_or_404(POSSale, id=sale_id)

    # Check permissions
    if not (request.user.is_superuser or request.user.role in ["admin", "manager"] or sale.cashier == request.user):
        messages.error(request, "You don't have permission to download this receipt.")
        return redirect("pos:sale_detail", sale_id=sale_id)

    try:
        # Get or create receipt
        receipt, created = Receipt.objects.get_or_create(
            sale=sale,
            defaults={
                "receipt_number": f"RCP-{uuid.uuid4().hex[:8].upper()}",
                "content": f"Receipt for sale {sale.sale_number}",
            },
        )

        # Generate PDF
        pdf_buffer = receipt.generate_pdf()

        # Create response
        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="receipt_{sale.sale_number}.pdf"'

        return response

    except Exception as e:
        messages.error(request, f"Error generating receipt: {str(e)}")
        return redirect("pos:sale_detail", sale_id=sale_id)


@login_required
def pos_receipt_print(request, sale_id):
    """Print receipt to external printer."""
    from .printer import ReceiptPrinter
    from core.models import SiteSettings
    
    sale = get_object_or_404(POSSale, id=sale_id)
    
    # Check permissions
    if not (request.user.is_superuser or request.user.role in ["admin", "manager"] or sale.cashier == request.user):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
    
    try:
        # Get printer settings
        settings = SiteSettings.objects.first()
        if not settings or not settings.printer_enabled:
            return JsonResponse({"success": False, "error": "Printer not configured or disabled"}, status=400)
        
        # Prepare connection parameters
        connection_params = {}
        if settings.printer_type == 'network':
            connection_params = {
                'host': settings.printer_host,
                'port': settings.printer_port,
                'timeout': 5
            }
            printer_name = None
        elif settings.printer_type == 'serial':
            connection_params = {
                'port': settings.printer_serial_port,
                'baudrate': settings.printer_baudrate,
                'timeout': 5
            }
            printer_name = None
        else:  # system
            printer_name = settings.printer_name
        
        # Initialize printer
        printer = ReceiptPrinter(
            printer_type=settings.printer_type,
            printer_name=printer_name,
            connection_params=connection_params
        )
        
        # Print receipt
        printer.print_receipt(sale)
        
        return JsonResponse({
            "success": True,
            "message": "Receipt sent to printer successfully"
        })
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error printing receipt: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": f"Failed to print receipt: {str(e)}"
        }, status=500)


@login_required
def pos_printer_test(request):
    """Test printer connection and print test page."""
    from .printer import ReceiptPrinter
    from core.models import SiteSettings
    
    if not (request.user.is_superuser or request.user.role in ["admin", "manager"]):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
    
    try:
        settings = SiteSettings.objects.first()
        if not settings or not settings.printer_enabled:
            return JsonResponse({"success": False, "error": "Printer not configured or disabled"}, status=400)
        
        # Prepare connection parameters
        connection_params = {}
        if settings.printer_type == 'network':
            connection_params = {
                'host': settings.printer_host,
                'port': settings.printer_port,
                'timeout': 5
            }
            printer_name = None
        elif settings.printer_type == 'serial':
            connection_params = {
                'port': settings.printer_serial_port,
                'baudrate': settings.printer_baudrate,
                'timeout': 5
            }
            printer_name = None
        else:  # system
            printer_name = settings.printer_name
        
        # Initialize printer
        printer = ReceiptPrinter(
            printer_type=settings.printer_type,
            printer_name=printer_name,
            connection_params=connection_params
        )
        
        # Print test page
        printer.test_print()
        
        return JsonResponse({
            "success": True,
            "message": "Test print sent successfully"
        })
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error in test print: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": f"Failed to print test page: {str(e)}"
        }, status=500)


@login_required
def pos_printer_list(request):
    """Get list of available system printers."""
    from .printer import get_available_printers
    
    if not (request.user.is_superuser or request.user.role in ["admin", "manager"]):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
    
    try:
        printers = get_available_printers()
        return JsonResponse({
            "success": True,
            "printers": printers
        })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting printer list: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": f"Failed to get printer list: {str(e)}"
        }, status=500)


@login_required
def pos_analytics(request):
    """POS analytics and reporting with comprehensive metrics matching main analytics."""

    from datetime import timedelta
    import json
    
    # Get period selection from request (daily, weekly, monthly, annual)
    period = request.GET.get("period", "weekly")  # Default to weekly
    
    # Get date ranges for analytics
    end_date = timezone.now()
    today = end_date.date()
    
    # Calculate date ranges based on selected period
    if period == "daily":
        start_date = end_date - timedelta(days=30)  # Last 30 days for daily view
        period_start = end_date - timedelta(days=1)
        prev_period_start = period_start - timedelta(days=1)
        prev_period_end = period_start
    elif period == "weekly":
        start_date = end_date - timedelta(days=84)  # Last 12 weeks
        period_start = end_date - timedelta(days=7)
        prev_period_start = period_start - timedelta(days=7)
        prev_period_end = period_start
    elif period == "monthly":
        start_date = end_date - timedelta(days=365)  # Last 12 months
        period_start = end_date - timedelta(days=30)
        prev_period_start = period_start - timedelta(days=30)
        prev_period_end = period_start
    else:  # annual
        start_date = end_date - timedelta(days=365*3)  # Last 3 years
        period_start = end_date - timedelta(days=365)
        prev_period_start = period_start - timedelta(days=365)
        prev_period_end = period_start
    
    week_start = end_date - timedelta(days=7)
    month_start = end_date - timedelta(days=30)
    year_start = end_date - timedelta(days=365)
    
    # Previous periods for comparison
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start
    prev_month_start = month_start - timedelta(days=30)
    prev_month_end = month_start

    # Get sales data for current period
    sales = POSSale.objects.filter(
        created_at__range=[start_date, end_date],
        status="completed"
    )
    
    # Period sales
    period_sales = POSSale.objects.filter(
        created_at__range=[period_start, end_date],
        status="completed"
    )
    prev_period_sales = POSSale.objects.filter(
        created_at__range=[prev_period_start, prev_period_end],
        status="completed"
    )

    # Calculate metrics
    total_sales = sales.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    total_transactions = sales.count()
    total_tax = sales.aggregate(tax=Sum("tax_amount"))["tax"] or Decimal("0.00")
    total_discounts = sales.aggregate(discounts=Sum("discount_amount"))["discounts"] or Decimal("0.00")
    
    # Period metrics
    period_total = period_sales.aggregate(total=Sum("total_amount"), count=Count("id"))
    prev_period_total = prev_period_sales.aggregate(total=Sum("total_amount"), count=Count("id"))
    
    period_revenue = float(period_total["total"] or Decimal("0.00"))
    period_transactions = period_total["count"] or 0
    prev_period_revenue = float(prev_period_total["total"] or Decimal("0.00"))
    prev_period_transactions = prev_period_total["count"] or 0
    
    period_growth = (
        ((period_revenue - prev_period_revenue) / prev_period_revenue * 100)
        if prev_period_revenue > 0 else 0
    )

    # Weekly sales for metric card
    weekly_sales_current = float(
        POSSale.objects.filter(
            created_at__range=[week_start, end_date],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    )
    weekly_sales_prev = float(
        POSSale.objects.filter(
            created_at__range=[prev_week_start, prev_week_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    )
    weekly_sales_growth = (
        ((weekly_sales_current - weekly_sales_prev) / weekly_sales_prev * 100)
        if weekly_sales_prev > 0 else 0
    )
    weekly_trend = [float(weekly_sales_current * (0.8 + (i * 0.05))) for i in range(7)]

    # Payment method breakdown
    payment_methods = (
        sales.values("payment_method")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("-total")
    )
    
    payment_chart_data = {
        "labels": [item["payment_method"] or "Unknown" for item in payment_methods],
        "datasets": [{
            "data": [float(item["total"]) for item in payment_methods],
            "backgroundColor": [
                "rgba(59, 130, 246, 0.8)",
                "rgba(16, 185, 129, 0.8)",
                "rgba(234, 179, 8, 0.8)",
                "rgba(239, 68, 68, 0.8)",
                "rgba(139, 92, 246, 0.8)",
            ],
            "borderWidth": 0
        }]
    }

    # Top products
    top_products = list(
        POSSaleItem.objects.filter(
            sale__created_at__range=[month_start, end_date],
            sale__status="completed"
        )
        .select_related("product", "product__category", "sale")
        .values("product__name", "product__category__name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum("total_price")
        )
        .order_by("-total_revenue")[:10]
    )

    # Category sales
    category_sales = (
        POSSaleItem.objects.filter(
            sale__created_at__range=[month_start, end_date],
            sale__status="completed"
        )
        .values("product__category__name")
        .annotate(total_revenue=Sum("total_price"))
        .order_by("-total_revenue")[:5]
    )
    
    category_pie_data = {
        "labels": [item["product__category__name"] or "Uncategorized" for item in category_sales],
        "datasets": [{
            "data": [float(item["total_revenue"]) for item in category_sales],
            "backgroundColor": [
                "rgba(59, 130, 246, 0.8)",
                "rgba(234, 179, 8, 0.8)",
                "rgba(16, 185, 129, 0.8)",
                "rgba(239, 68, 68, 0.8)",
                "rgba(139, 92, 246, 0.8)",
            ],
            "borderWidth": 0
        }]
    }

    # Monthly bar chart
    monthly_comparison = []
    monthly_labels = []
    for i in range(9):
        month_end = end_date - timedelta(days=30*i)
        month_start_date = month_end - timedelta(days=30)
        month_sales = POSSale.objects.filter(
            created_at__range=[month_start_date, month_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        monthly_comparison.append(float(month_sales))
        monthly_labels.append(month_end.strftime("%b"))
    
    monthly_comparison.reverse()
    monthly_labels.reverse()
    
    current_year_total = sum(monthly_comparison[-12:]) if len(monthly_comparison) >= 12 else sum(monthly_comparison)
    prev_year_start = year_start - timedelta(days=365)
    prev_year_total = POSSale.objects.filter(
        created_at__range=[prev_year_start, year_start],
        status="completed"
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    year_growth = (
        ((current_year_total - float(prev_year_total)) / float(prev_year_total) * 100)
        if prev_year_total > 0 else 0
    )
    
    monthly_bar_data = {
        "labels": monthly_labels,
        "datasets": [{
            "label": "Monthly Sales",
            "data": monthly_comparison,
            "backgroundColor": "rgba(22, 163, 74, 0.8)",
            "borderColor": "rgba(22, 163, 74, 1)",
            "borderWidth": 1
        }]
    }

    # Period chart data
    period_chart_labels = []
    period_chart_data = []
    
    if period == "daily":
        for i in range(30):
            day = end_date - timedelta(days=29-i)
            day_sales = POSSale.objects.filter(
                created_at__date=day.date(),
                status="completed"
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
            period_chart_labels.append(day.strftime("%b %d"))
            period_chart_data.append(float(day_sales))
    elif period == "weekly":
        for i in range(12):
            week_end = end_date - timedelta(days=7*(11-i))
            week_start_date = week_end - timedelta(days=7)
            week_sales = POSSale.objects.filter(
                created_at__range=[week_start_date, week_end],
                status="completed"
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
            period_chart_labels.append(week_end.strftime("%b %d"))
            period_chart_data.append(float(week_sales))
    elif period == "monthly":
        for i in range(12):
            month_end = end_date - timedelta(days=30*(11-i))
            month_start_date = month_end - timedelta(days=30)
            month_sales = POSSale.objects.filter(
                created_at__range=[month_start_date, month_end],
                status="completed"
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
            period_chart_labels.append(month_end.strftime("%b %Y"))
            period_chart_data.append(float(month_sales))
    else:  # annual
        for i in range(3):
            year_end = end_date - timedelta(days=365*(2-i))
            year_start_date = year_end - timedelta(days=365)
            year_sales = POSSale.objects.filter(
                created_at__range=[year_start_date, year_end],
                status="completed"
            ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
            period_chart_labels.append(year_end.strftime("%Y"))
            period_chart_data.append(float(year_sales))
    
    period_chart = {
        "labels": period_chart_labels,
        "datasets": [{
            "label": f"{period.capitalize()} Sales",
            "data": period_chart_data,
            "borderColor": "rgba(22, 163, 74, 1)",
            "backgroundColor": "rgba(22, 163, 74, 0.1)",
            "tension": 0.4,
            "fill": True
        }]
    }

    # Daily, weekly, monthly, annual summaries
    daily_sales_data = []
    for i in range(7):
        day = end_date - timedelta(days=6-i)
        day_total = POSSale.objects.filter(
            created_at__date=day.date(),
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        daily_sales_data.append({"date": day.date(), "total": float(day_total)})
    
    weekly_sales_data = []
    for i in range(7):
        week_end = end_date - timedelta(days=7*(6-i))
        week_start_date = week_end - timedelta(days=7)
        week_total = POSSale.objects.filter(
            created_at__range=[week_start_date, week_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        weekly_sales_data.append({"week": week_end.date(), "total": float(week_total)})
    
    monthly_sales_data = []
    for i in range(7):
        month_end = end_date - timedelta(days=30*(6-i))
        month_start_date = month_end - timedelta(days=30)
        month_total = POSSale.objects.filter(
            created_at__range=[month_start_date, month_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        monthly_sales_data.append({"month": month_end.date(), "total": float(month_total)})
    
    annual_sales_data = []
    for i in range(3):
        year_end = end_date - timedelta(days=365*(2-i))
        year_start_date = year_end - timedelta(days=365)
        year_total = POSSale.objects.filter(
            created_at__range=[year_start_date, year_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        annual_sales_data.append({"year": year_end.year, "total": float(year_total)})

    # Conversion rate
    total_sales_attempts = POSSale.objects.filter(
        created_at__range=[month_start, end_date]
    ).count()
    completed_sales = POSSale.objects.filter(
        created_at__range=[month_start, end_date],
        status="completed"
    ).count()
    conversion_rate = (
        (completed_sales / total_sales_attempts * 100)
        if total_sales_attempts > 0 else 0
    )
    
    prev_completed = POSSale.objects.filter(
        created_at__range=[prev_month_start, prev_month_end],
        status="completed"
    ).count()
    prev_total = POSSale.objects.filter(
        created_at__range=[prev_month_start, prev_month_end]
    ).count()
    prev_conversion_rate = (
        (prev_completed / prev_total * 100)
        if prev_total > 0 else 0
    )
    conversion_growth = conversion_rate - prev_conversion_rate

    # Recent sales
    recent_sales = POSSale.objects.filter(
        status="completed"
    ).select_related("cashier", "seller").order_by("-created_at")[:5]

    context = {
        # Period data
        "period": period,
        "period_revenue": period_revenue,
        "period_transactions": period_transactions,
        "period_growth": period_growth,
        "period_growth_abs": abs(period_growth),
        "period_chart": json.dumps(period_chart),
        # Overall metrics
        "total_sales": total_sales,
        "total_transactions": total_transactions,
        "total_tax": total_tax,
        "total_discounts": total_discounts,
        # Weekly sales metric
        "weekly_sales": {
            "value": weekly_sales_current,
            "growth": weekly_sales_growth,
            "growth_abs": abs(weekly_sales_growth),
            "trend": json.dumps(weekly_trend),
            "formatted": f"KSh {weekly_sales_current:,.0f}"
        },
        # Charts data
        "category_pie_data": json.dumps(category_pie_data),
        "payment_chart_data": json.dumps(payment_chart_data),
        "monthly_bar_data": json.dumps(monthly_bar_data),
        "year_growth": year_growth,
        "year_growth_abs": abs(year_growth),
        # Summary tables
        "daily_sales_data": daily_sales_data,
        "weekly_sales_data": weekly_sales_data,
        "monthly_sales_data": monthly_sales_data,
        "annual_sales_data": annual_sales_data,
        # Top products
        "top_products": top_products,
        # Conversion rates
        "conversion_rate": conversion_rate,
        "conversion_growth": conversion_growth,
        "conversion_growth_abs": abs(conversion_growth),
        # Recent activity
        "recent_sales": recent_sales,
        # Payment breakdown (for table)
        "payment_breakdown": payment_methods,
    }

    return render(request, "pos/analytics.html", context)


@login_required
def toggle_offline_mode(request):
    """Toggle offline mode for current POS session."""
    if not request.user.can_access_pos():
        return JsonResponse({"success": False, "error": "Permission denied"})

    active_session = POSSession.objects.filter(cashier=request.user, status__in=["open", "offline"]).first()

    if not active_session:
        return JsonResponse({"success": False, "error": "No active session"})

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "start_offline":
            active_session.start_offline_mode()
            return JsonResponse({"success": True, "message": "Offline mode activated", "status": "offline"})
        elif action == "end_offline":
            active_session.end_offline_mode()
            return JsonResponse({"success": True, "message": "Offline mode deactivated", "status": "online"})

    return JsonResponse({"success": False, "error": "Invalid action"})


@login_required
def sync_offline_transactions(request):
    """Sync offline transactions to server."""
    if not request.user.can_access_pos():
        return JsonResponse({"success": False, "error": "Permission denied"})

    if request.method == "POST":
        try:
            # Get pending offline transactions
            pending_transactions = OfflineTransaction.objects.filter(sync_status="pending")

            synced_count = 0
            failed_count = 0

            for pending_transaction in pending_transactions:
                try:
                    pending_transaction.mark_syncing()

                    # Create actual POSSale record
                    sale = POSSale.objects.create(
                        session=pending_transaction.session,
                        cashier=request.user,
                        customer_name=pending_transaction.customer_name,
                        customer_phone=pending_transaction.customer_phone,
                        customer_email=pending_transaction.customer_email,
                        payment_method=pending_transaction.payment_method,
                        subtotal=pending_transaction.subtotal,
                        tax_amount=pending_transaction.tax_amount,
                        discount_amount=pending_transaction.discount_amount,
                        total_amount=pending_transaction.total_amount,
                        status="completed",
                        payment_status="paid",
                    )

                    # Create sale items
                    for item_data in pending_transaction.get_items_data():
                        product = Product.objects.get(id=item_data["product_id"])
                        POSSaleItem.objects.create(
                            sale=sale,
                            product=product,
                            quantity=item_data["quantity"],
                            unit_price=item_data["unit_price"],
                            total_price=item_data["total_price"],
                        )

                    # Mark as synced
                    pending_transaction.mark_synced()
                    synced_count += 1

                except Exception as e:
                    transaction.mark_sync_failed(str(e))
                    failed_count += 1

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Synced {synced_count} transactions, {failed_count} failed",
                    "synced_count": synced_count,
                    "failed_count": failed_count,
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})


@login_required
def offline_transactions_list(request):
    """List all offline transactions."""
    if not request.user.can_access_pos():
        messages.error(request, "You don't have permission to access POS.")
        return redirect("core:home")

    offline_transactions = OfflineTransaction.objects.filter(session__cashier=request.user).order_by(
        "-created_offline_at"
    )

    context = {"page_title": "Offline Transactions", "offline_transactions": offline_transactions}

    return render(request, "pos/offline_transactions.html", context)


@login_required
def offline_sale_create(request):
    """Create a sale in offline mode."""
    if not request.user.can_access_pos():
        return JsonResponse({"success": False, "error": "Permission denied"})

    # Get active session
    active_session = POSSession.objects.filter(cashier=request.user, status__in=["open", "offline"]).first()

    if not active_session:
        return JsonResponse({"success": False, "error": "No active session"})

    if request.method == "POST":
        try:
            data = json.loads(request.body)

            # Check if we're in offline mode
            if active_session.is_offline:
                # Store offline transaction
                offline_transaction = OfflineTransaction.objects.create(
                    session=active_session,
                    local_transaction_id=data.get("local_id"),
                    customer_name=data.get("customer_name", ""),
                    customer_phone=data.get("customer_phone", ""),
                    customer_email=data.get("customer_email", ""),
                    items_data=json.dumps(data.get("items", [])),
                    payment_method=data.get("payment_method", "cash"),
                    subtotal=Decimal(data.get("subtotal", 0)),
                    tax_amount=Decimal(data.get("tax_amount", 0)),
                    discount_amount=Decimal(data.get("discount_amount", 0)),
                    total_amount=Decimal(data.get("total_amount", 0)),
                    device_info=json.dumps(data.get("device_info", {})),
                    app_version=data.get("app_version", ""),
                )

                return JsonResponse(
                    {
                        "success": True,
                        "message": "Sale stored offline successfully",
                        "offline_id": offline_transaction.local_transaction_id,
                    }
                )
            else:
                # Create online sale using existing functionality
                return pos_sale_create(request)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON data"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method"})


@login_required
def check_connection_status(request):
    """Check if the system can connect to the server."""
    try:
        # Simple connection test
        from django.db import connection

        connection.ensure_connection()

        return JsonResponse({"success": True, "online": True, "message": "Connected to server"})
    except Exception as e:
        return JsonResponse(
            {"success": True, "online": False, "message": "Offline mode - no server connection", "error": str(e)}
        )

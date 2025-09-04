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
from decimal import Decimal
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
    }

    return render(request, "pos/dashboard.html", context)


@login_required
def pos_sale_create(request):
    """Create a new POS sale with enhanced features."""

    if request.method == "POST":
        try:
            with transaction.atomic():
                # Get active session
                active_session = get_object_or_404(POSSession, cashier=request.user, status="open")

                # Create sale
                sale_data = json.loads(request.body)

                sale = POSSale.objects.create(
                    session=active_session,
                    cashier=request.user,
                    seller=active_session.seller,
                    customer_name=sale_data.get("customer_name", ""),
                    customer_phone=sale_data.get("customer_phone", ""),
                    customer_email=sale_data.get("customer_email", ""),
                    payment_method=sale_data.get("payment_method", "cash"),
                    tax_rate_id=sale_data.get("tax_rate_id"),
                    notes=sale_data.get("notes", ""),
                )

                # Add items
                total_amount = Decimal("0.00")
                for item_data in sale_data.get("items", []):
                    product = get_object_or_404(Product, id=item_data["product_id"])
                    quantity = int(item_data["quantity"])
                    unit_price = Decimal(item_data["unit_price"])

                    # Check stock
                    if product.stock_quantity < quantity:
                        raise ValueError(f"Insufficient stock for {product.name}")

                    # Create sale item
                    sale_item = POSSaleItem.objects.create(
                        sale=sale, product=product, quantity=quantity, unit_price=unit_price
                    )

                    # Apply item discounts if any
                    for discount_id in item_data.get("discounts", []):
                        try:
                            discount = Discount.objects.get(id=discount_id)
                            sale_item.apply_item_discount(discount)
                        except Discount.DoesNotExist:
                            # Log the error for debugging
                            import logging

                            logger = logging.getLogger(__name__)
                            logger.warning(f"Discount with ID {discount_id} not found for sale item")

                    total_amount += sale_item.total_price

                # Apply sale-level discounts
                for discount_id in sale_data.get("sale_discounts", []):
                    try:
                        discount = Discount.objects.get(id=discount_id)
                        sale.apply_discount(discount)
                    except Discount.DoesNotExist:
                        # Log the error for debugging
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.warning(f"Discount with ID {discount_id} not found for sale")

                # Calculate change
                amount_paid = Decimal(sale_data.get("amount_paid", "0.00"))
                sale.change_amount = amount_paid - sale.total_amount

                # Mark as completed
                sale.status = "completed"
                sale.payment_status = "paid"
                sale.save()

                # Generate receipt
                receipt = Receipt.objects.create(
                    receipt_number=f"RCP-{uuid.uuid4().hex[:8].upper()}",
                    sale=sale,
                    content=f"Receipt for sale {sale.sale_number}",
                )

                return JsonResponse(
                    {
                        "success": True,
                        "sale_id": sale.id,
                        "sale_number": sale.sale_number,
                        "total_amount": str(sale.total_amount),
                        "receipt_number": receipt.receipt_number,
                    }
                )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

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
        "items": sale.items.all(),
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

    context = {
        "page_obj": page_obj,
        "total_sales": sales.count(),
        "total_amount": sales.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00"),
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
    """Search products for POS sale."""

    query = request.GET.get("q", "")
    category_id = request.GET.get("category")

    products = Product.objects.filter(is_active=True, stock_quantity__gt=0)

    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query))

    if category_id:
        products = products.filter(category_id=category_id)

    # Limit results
    products = products[:20]

    results = []
    for product in products:
        results.append(
            {
                "id": product.id,
                "name": product.name,
                "price": str(product.price),
                "stock_quantity": product.stock_quantity,
                "sku": product.sku,
                "category": product.category.name,
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
def pos_analytics(request):
    """POS analytics and reporting."""

    # Get date range
    date_from = request.GET.get("date_from", timezone.now().date())
    date_to = request.GET.get("date_to", timezone.now().date())

    # Get sales data
    sales = POSSale.objects.filter(created_at__date__range=[date_from, date_to], status="completed")

    # Calculate metrics
    total_sales = sales.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    total_transactions = sales.count()
    total_tax = sales.aggregate(tax=Sum("tax_amount"))["tax"] or Decimal("0.00")
    total_discounts = sales.aggregate(discounts=Sum("discount_amount"))["discounts"] or Decimal("0.00")

    # Payment method breakdown
    payment_breakdown = sales.values("payment_method").annotate(count=Count("id"), total=Sum("total_amount"))

    # Top products
    top_products = (
        sales.values("items__product__name")
        .annotate(quantity=Sum("items__quantity"), revenue=Sum("items__total_price"))
        .order_by("-revenue")[:10]
    )

    # Daily sales trend
    daily_sales = (
        sales.extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(sales=Sum("total_amount"), transactions=Count("id"))
        .order_by("day")
    )

    context = {
        "date_from": date_from,
        "date_to": date_to,
        "total_sales": total_sales,
        "total_transactions": total_transactions,
        "total_tax": total_tax,
        "total_discounts": total_discounts,
        "payment_breakdown": payment_breakdown,
        "top_products": top_products,
        "daily_sales": daily_sales,
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
                    for item_data in pending_transaction.items_data:
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
                    items_data=data.get("items", []),
                    payment_method=data.get("payment_method", "cash"),
                    subtotal=Decimal(data.get("subtotal", 0)),
                    tax_amount=Decimal(data.get("tax_amount", 0)),
                    discount_amount=Decimal(data.get("discount_amount", 0)),
                    total_amount=Decimal(data.get("total_amount", 0)),
                    device_info=data.get("device_info", {}),
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

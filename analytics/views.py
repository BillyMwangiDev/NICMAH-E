"""
Analytics views with beautiful sales graphs and reports.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, ExtractHour, ExtractWeekDay
from django.utils import timezone
from django.contrib import messages
import json
from datetime import timedelta

from pos.models import POSSale, POSSaleItem
from catalog.models import Category, Product
from django.db.models import F
from users.models import CustomUser


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only admin users can access analytics."""

    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.role == "admin")


@login_required
def dashboard(request):
    """Analytics dashboard with role-based access control."""
    if not (request.user.is_staff or request.user.role == "admin"):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("core:home")

    # Get date range for analytics
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    # Daily sales data for the last 30 days
    daily_sales = (
        POSSale.objects.filter(created_at__range=[start_date, end_date], status="completed")
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("date")
    )

    # Weekly sales data for the last 12 weeks
    weekly_sales = (
        POSSale.objects.filter(created_at__range=[end_date - timedelta(weeks=12), end_date], status="completed")
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("week")
    )

    # Monthly sales data for the last 12 months
    monthly_sales = (
        POSSale.objects.filter(created_at__range=[end_date - timedelta(days=365), end_date], status="completed")
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("month")
    )

    # Top selling products
    top_products = (
        POSSaleItem.objects.filter(sale__created_at__range=[start_date, end_date], sale__status="completed")
        .values("product__name")
        .annotate(total_quantity=Sum("quantity"), total_revenue=Sum("total_price"))
        .order_by("-total_quantity")[:10]
    )

    # Sales by category
    category_sales = (
        POSSaleItem.objects.filter(sale__created_at__range=[start_date, end_date], sale__status="completed")
        .values("product__category__name")
        .annotate(total_revenue=Sum("total_price"), total_quantity=Sum("quantity"))
        .order_by("-total_revenue")
    )

    # Payment method distribution
    payment_methods = (
        POSSale.objects.filter(created_at__range=[start_date, end_date], status="completed")
        .values("payment_method")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("-total")
    )

    # Top performing sellers
    top_sellers = (
        POSSale.objects.filter(created_at__range=[start_date, end_date], status="completed", seller__isnull=False)
        .values("seller__username", "seller__first_name", "seller__last_name")
        .annotate(total_sales=Sum("total_amount"), total_transactions=Count("id"))
        .order_by("-total_sales")[:10]
    )

    # Sales by weekday (1=Sunday in Django ExtractWeekDay, map to Mon-Sun display)
    weekday_map = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
    sales_by_weekday_qs = (
        POSSale.objects.filter(created_at__range=[start_date, end_date], status="completed")
        .annotate(wd=ExtractWeekDay("created_at"))
        .values("wd")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("wd")
    )
    weekday_labels = [weekday_map[d] for d in [2,3,4,5,6,7,1]]  # Mon..Sun order
    weekday_totals_dict = {int(item["wd"]): float(item["total"]) for item in sales_by_weekday_qs}
    weekday_values = [weekday_totals_dict.get(d, 0.0) for d in [2,3,4,5,6,7,1]]

    # Low stock products (top 10)
    low_stock_products = (
        Product.objects.filter(is_active=True).filter(stock_quantity__lte=F("min_stock_level"))
        .order_by("stock_quantity")[:10]
    )

    # Prepare data for charts
    daily_chart_data = {
        "labels": [item["date"].strftime("%b %d") for item in daily_sales],
        "datasets": [
            {
                "label": "Daily Sales",
                "data": [float(item["total"]) for item in daily_sales],
                "borderColor": "rgb(34, 197, 94)",
                "backgroundColor": "rgba(34, 197, 94, 0.1)",
                "tension": 0.4,
                "fill": True,
            }
        ],
    }

    weekly_chart_data = {
        "labels": [item["week"].strftime("%b %d") for item in weekly_sales],
        "datasets": [
            {
                "label": "Weekly Sales",
                "data": [float(item["total"]) for item in weekly_sales],
                "borderColor": "rgb(59, 130, 246)",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "tension": 0.4,
                "fill": True,
            }
        ],
    }

    monthly_chart_data = {
        "labels": [item["month"].strftime("%B %Y") for item in monthly_sales],
        "datasets": [
            {
                "label": "Monthly Sales",
                "data": [float(item["total"]) for item in monthly_sales],
                "borderColor": "rgb(168, 85, 247)",
                "backgroundColor": "rgba(168, 85, 247, 0.1)",
                "tension": 0.4,
                "fill": True,
            }
        ],
    }

    category_chart_data = {
        "labels": [item["product__category__name"] or "Uncategorized" for item in category_sales],
        "datasets": [
            {
                "label": "Sales by Category",
                "data": [float(item["total_revenue"]) for item in category_sales],
                "backgroundColor": [
                    "#ef4444",
                    "#f97316",
                    "#f59e0b",
                    "#eab308",
                    "#84cc16",
                    "#22c55e",
                    "#10b981",
                    "#06b6d4",
                    "#3b82f6",
                    "#8b5cf6",
                ],
            }
        ],
    }

    payment_chart_data = {
        "labels": [item["payment_method"] or "Unknown" for item in payment_methods],
        "datasets": [
            {
                "label": "Payment Methods",
                "data": [float(item["total"]) for item in payment_methods],
                "backgroundColor": [
                    "#ef4444",
                    "#f97316",
                    "#f59e0b",
                    "#eab308",
                    "#84cc16",
                    "#22c55e",
                    "#10b981",
                    "#06b6d4",
                    "#3b82f6",
                    "#8b5cf6",
                ],
            }
        ],
    }

    weekday_chart_data = {
        "labels": weekday_labels,
        "datasets": [
            {
                "label": "Sales by Weekday",
                "data": weekday_values,
                "backgroundColor": "rgba(99, 102, 241, 0.6)",
                "borderColor": "rgb(99, 102, 241)",
            }
        ],
    }

    # Calculate summary statistics
    total_revenue = sum(item["total"] for item in daily_sales)
    total_transactions = sum(item["count"] for item in daily_sales)
    avg_transaction_value = total_revenue / total_transactions if total_transactions > 0 else 0

    # Growth calculations
    if len(daily_sales) >= 14:
        current_week_revenue = sum(item["total"] for item in daily_sales[-7:])
        previous_week_revenue = sum(item["total"] for item in daily_sales[-14:-7])
        weekly_growth = (
            ((current_week_revenue - previous_week_revenue) / previous_week_revenue * 100)
            if previous_week_revenue > 0
            else 0
        )
    else:
        weekly_growth = 0

    context = {
        "daily_chart_data": json.dumps(daily_chart_data),
        "weekly_chart_data": json.dumps(weekly_chart_data),
        "monthly_chart_data": json.dumps(monthly_chart_data),
        "category_chart_data": json.dumps(category_chart_data),
        "payment_chart_data": json.dumps(payment_chart_data),
        "weekday_chart_data": json.dumps(weekday_chart_data),
        "top_products": top_products,
        "top_sellers": top_sellers,
        "low_stock_products": low_stock_products,
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "avg_transaction_value": avg_transaction_value,
        "weekly_growth": weekly_growth,
        "daily_sales": daily_sales,
        "weekly_sales": weekly_sales,
        "monthly_sales": monthly_sales,
    }

    return render(request, "analytics/dashboard.html", context)


@login_required
def sales_report(request):
    """Detailed sales report with filtering options."""
    if not (request.user.is_staff or request.user.role == "admin"):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("core:home")

    # Get filter parameters
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    category = request.GET.get("category")
    seller = request.GET.get("seller")

    # Base queryset
    sales = POSSale.objects.filter(status="completed").select_related("seller", "cashier")

    # Apply filters
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)
    if category:
        sales = sales.filter(items__product__category__name=category)
    if seller:
        sales = sales.filter(seller__username=seller)

    # Group by date for chart
    sales_by_date = (
        sales.annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("date")
    )

    # Prepare chart data
    chart_data = {
        "labels": [item["date"].strftime("%b %d") for item in sales_by_date],
        "datasets": [
            {
                "label": "Sales",
                "data": [float(item["total"]) for item in sales_by_date],
                "borderColor": "rgb(34, 197, 94)",
                "backgroundColor": "rgba(34, 197, 94, 0.1)",
                "tension": 0.4,
                "fill": True,
            }
        ],
    }

    context = {
        "chart_data": json.dumps(chart_data),
        "sales": sales.order_by("-created_at"),
        "categories": Category.objects.all(),
        "sellers": CustomUser.objects.filter(role="seller"),
        "date_from": date_from,
        "date_to": date_to,
        "category": category,
        "seller": seller,
    }

    return render(request, "analytics/sales_report.html", context)


@login_required
def export_sales_data(request):
    """Export sales data to Excel."""
    if not (request.user.is_staff or request.user.role == "admin"):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("analytics:dashboard")

    try:
        import pandas as pd
        from openpyxl.styles import Font, PatternFill, Alignment
        import io

        # Get filter parameters
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")

        # Base queryset
        sales = POSSale.objects.filter(status="completed").select_related("seller", "cashier")

        # Apply filters
        if date_from:
            sales = sales.filter(created_at__date__gte=date_from)
        if date_to:
            sales = sales.filter(created_at__date__lte=date_to)

        # Create DataFrame
        data = []
        for sale in sales:
            data.append(
                {
                    "Sale ID": sale.sale_number,
                    "Date": sale.created_at.strftime("%Y-%m-%d %H:%M"),
                    "Customer": sale.customer_name or "Walk-in Customer",
                    "Seller": sale.seller.username if sale.seller else "N/A",
                    "Cashier": sale.cashier.username,
                    "Payment Method": sale.payment_method,
                    "Subtotal": float(sale.subtotal),
                    "Tax": float(sale.tax_amount),
                    "Discount": float(sale.discount_amount),
                    "Total": float(sale.total_amount),
                    "Status": sale.status,
                }
            )

        df = pd.DataFrame(data)

        # Create Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sales Data", index=False)

            # Get the worksheet
            worksheet = writer.sheets["Sales Data"]

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
        from django.http import HttpResponse

        response = HttpResponse(
            output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = (
            f'attachment; filename="sales_data_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
        )

        return response

    except Exception as e:
        messages.error(request, f"Error exporting sales data: {str(e)}")
        return redirect("analytics:dashboard")


@login_required
def seller_dashboard(request):
    """Limited analytics dashboard for sellers."""
    if request.user.role != "seller":
        messages.error(request, "Access denied. Seller privileges required.")
        return redirect("core:home")

    # Get seller's sales data
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    # Seller's daily sales
    daily_sales = (
        POSSale.objects.filter(seller=request.user, created_at__range=[start_date, end_date], status="completed")
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("date")
    )

    # Seller's top products
    top_products = (
        POSSaleItem.objects.filter(
            sale__seller=request.user, sale__created_at__range=[start_date, end_date], sale__status="completed"
        )
        .values("product__name")
        .annotate(total_quantity=Sum("quantity"), total_revenue=Sum("total_price"))
        .order_by("-total_quantity")[:5]
    )

    # Prepare chart data
    daily_chart_data = {
        "labels": [item["date"].strftime("%b %d") for item in daily_sales],
        "datasets": [
            {
                "label": "Your Daily Sales",
                "data": [float(item["total"]) for item in daily_sales],
                "borderColor": "rgb(34, 197, 94)",
                "backgroundColor": "rgba(34, 197, 94, 0.1)",
                "tension": 0.4,
                "fill": True,
            }
        ],
    }

    # Calculate seller statistics
    total_revenue = sum(item["total"] for item in daily_sales)
    total_transactions = sum(item["count"] for item in daily_sales)
    avg_transaction_value = total_revenue / total_transactions if total_transactions > 0 else 0

    context = {
        "daily_chart_data": json.dumps(daily_chart_data),
        "top_products": top_products,
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "avg_transaction_value": avg_transaction_value,
    }

    return render(request, "analytics/seller_dashboard.html", context)

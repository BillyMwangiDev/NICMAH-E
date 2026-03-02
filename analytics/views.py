"""
Analytics views with beautiful sales graphs and reports.
Optimized with proper select_related and prefetch_related for all relationships.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, ExtractHour, ExtractWeekDay
from django.utils import timezone
from django.contrib import messages
import json
from datetime import timedelta
from decimal import Decimal

from catalog.models import Category, Product
from users.models import CustomUser
from analytics.models import Sales, SalesItem


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only admin users can access analytics."""

    def test_func(self):
        return self.request.user.is_authenticated and (self.request.user.is_staff or self.request.user.role == "admin")


@login_required
def dashboard(request):
    """Modern analytics dashboard with comprehensive metrics and period tracking."""
    if not (request.user.is_staff or request.user.role == "admin"):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("core:home")

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

    # ========== METRIC 1: WEEKLY SALES ==========
    # Use unified Sales model to track ALL sales (POS, e-commerce, manual)
    weekly_sales_current = Sales.objects.filter(
        created_at__range=[week_start, end_date],
        status="completed"
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    
    weekly_sales_previous = Sales.objects.filter(
        created_at__range=[prev_week_start, prev_week_end],
        status="completed"
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    
    weekly_sales_growth = (
        ((weekly_sales_current - weekly_sales_previous) / weekly_sales_previous * 100)
        if weekly_sales_previous > 0
        else 0
    )
    
    # Weekly sales trend (last 7 days for mini chart)
    weekly_trend = []
    for i in range(7):
        day = end_date - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        day_sales = Sales.objects.filter(
            created_at__range=[day_start, day_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        weekly_trend.append(float(day_sales))

    # ========== METRIC 2: NEW USERS/CUSTOMERS ==========
    new_users_current = CustomUser.objects.filter(
        date_joined__range=[week_start, end_date]
    ).count()
    
    new_users_previous = CustomUser.objects.filter(
        date_joined__range=[prev_week_start, prev_week_end]
    ).count()
    
    new_users_growth = (
        ((new_users_current - new_users_previous) / new_users_previous * 100)
        if new_users_previous > 0
        else 0
    )
    
    # New users trend (last 7 days)
    new_users_trend = []
    for i in range(7):
        day = end_date - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        day_users = CustomUser.objects.filter(
            date_joined__range=[day_start, day_end]
        ).count()
        new_users_trend.append(day_users)

    # ========== METRIC 3: PURCHASE ORDERS (TRANSACTIONS) ==========
    # Use unified Sales model to track ALL sales transactions
    orders_current = Sales.objects.filter(
        created_at__range=[week_start, end_date],
        status="completed"
    ).count()
    
    orders_previous = Sales.objects.filter(
        created_at__range=[prev_week_start, prev_week_end],
        status="completed"
    ).count()
    
    orders_growth = (
        ((orders_current - orders_previous) / orders_previous * 100)
        if orders_previous > 0
        else 0
    )
    
    # Orders trend (last 7 days)
    orders_trend = []
    for i in range(7):
        day = end_date - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        day_orders = Sales.objects.filter(
            created_at__range=[day_start, day_end],
            status="completed"
        ).count()
        orders_trend.append(day_orders)

    # ========== METRIC 4: PRODUCTS SOLD ==========
    # Use unified SalesItem model to track ALL products sold
    products_sold_current = SalesItem.objects.filter(
        sale__created_at__range=[week_start, end_date],
        sale__status="completed"
    ).aggregate(total=Sum("quantity"))["total"] or 0
    
    products_sold_previous = SalesItem.objects.filter(
        sale__created_at__range=[prev_week_start, prev_week_end],
        sale__status="completed"
    ).aggregate(total=Sum("quantity"))["total"] or 0
    
    products_sold_growth = (
        ((products_sold_current - products_sold_previous) / products_sold_previous * 100)
        if products_sold_previous > 0
        else 0
    )
    
    # Products sold trend (last 7 days) - OPTIMIZED with select_related
    products_trend = []
    for i in range(7):
        day = end_date - timedelta(days=6-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        day_products = SalesItem.objects.filter(
            sale__created_at__range=[day_start, day_end],
            sale__status="completed"
        ).select_related("sale", "product").aggregate(total=Sum("quantity"))["total"] or 0
        products_trend.append(day_products)

    # ========== PIE CHART: SALES BY CATEGORY ==========
    # OPTIMIZED: Using select_related for product and category - ALL sales
    category_sales = (
        SalesItem.objects.filter(
            sale__created_at__range=[month_start, end_date],
            sale__status="completed"
        )
        .select_related("product", "product__category", "sale")
        .values("product__category__name")
        .annotate(total_revenue=Sum("total_price"), total_quantity=Sum("quantity"))
        .order_by("-total_revenue")[:4]
    )
    
    category_pie_data = {
        "labels": [item["product__category__name"] or "Uncategorized" for item in category_sales],
        "datasets": [{
                "data": [float(item["total_revenue"]) for item in category_sales],
                "backgroundColor": [
                "rgba(59, 130, 246, 0.8)",  # Blue
                "rgba(234, 179, 8, 0.8)",    # Yellow
                "rgba(16, 185, 129, 0.8)",   # Teal
                "rgba(239, 68, 68, 0.8)",    # Red
            ],
            "borderWidth": 0
        }]
    }
    
    # ========== PAYMENT METHODS DISTRIBUTION ==========
    # ALL sales payment methods
    payment_methods = (
        Sales.objects.filter(
            created_at__range=[month_start, end_date],
            status="completed"
        )
        .values("payment_method")
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

    # ========== BAR CHART: MONTHLY SALES COMPARISON ==========
    # Get last 9 months of data - ALL sales
    monthly_comparison = []
    monthly_labels = []
    for i in range(9):
        month_end = end_date - timedelta(days=30*i)
        month_start_date = month_end - timedelta(days=30)
        month_sales = Sales.objects.filter(
            created_at__range=[month_start_date, month_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
        monthly_comparison.append(float(month_sales))
        monthly_labels.append(month_end.strftime("%b"))
    
    monthly_comparison.reverse()
    monthly_labels.reverse()
    
    # Calculate year-over-year growth
    current_year_total = sum(monthly_comparison[-12:]) if len(monthly_comparison) >= 12 else sum(monthly_comparison)
    prev_year_start = year_start - timedelta(days=365)
    prev_year_total = Sales.objects.filter(
        created_at__range=[prev_year_start, year_start],
        status="completed"
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    year_growth = (
        ((current_year_total - float(prev_year_total)) / float(prev_year_total) * 100)
        if prev_year_total > 0
            else 0
    )
    
    monthly_bar_data = {
        "labels": monthly_labels,
        "datasets": [{
            "label": "Monthly Sales",
            "data": monthly_comparison,
            "backgroundColor": "rgba(59, 130, 246, 0.8)",
            "borderColor": "rgba(59, 130, 246, 1)",
            "borderWidth": 1
        }]
    }

    # ========== TOP PERFORMING PRODUCTS ==========
    # OPTIMIZED: Using select_related for product and category - ALL sales
    top_products = list(
        SalesItem.objects.filter(
            sale__created_at__range=[month_start, end_date],
            sale__status="completed"
        )
        .select_related("product", "product__category", "sale")
        .values("product__name", "product__price", "product__category__name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum("total_price")
        )
        .order_by("-total_quantity")[:10]
    )

    # ========== CONVERSION RATES ==========
    # Calculate conversion rate (completed sales / total sales attempts) - ALL sales
    total_sales_attempts = Sales.objects.filter(
        created_at__range=[month_start, end_date]
    ).count()
    completed_sales = Sales.objects.filter(
        created_at__range=[month_start, end_date],
        status="completed"
    ).count()
    conversion_rate = (
        (completed_sales / total_sales_attempts * 100)
        if total_sales_attempts > 0
        else 0
    )
    
    # Previous month conversion rate
    prev_completed = Sales.objects.filter(
        created_at__range=[prev_month_start, prev_month_end],
        status="completed"
    ).count()
    prev_total = Sales.objects.filter(
        created_at__range=[prev_month_start, prev_month_end]
    ).count()
    prev_conversion_rate = (
        (prev_completed / prev_total * 100)
        if prev_total > 0
        else 0
    )
    conversion_growth = conversion_rate - prev_conversion_rate

    # ========== PERIOD-BASED SALES DATA ==========
    # Daily sales data - ALL sales
    daily_sales_data = (
        Sales.objects.filter(
            created_at__range=[end_date - timedelta(days=30), end_date],
            status="completed"
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("date")
    )

    # Weekly sales data - ALL sales
    weekly_sales_data = (
        Sales.objects.filter(
            created_at__range=[end_date - timedelta(weeks=12), end_date],
            status="completed"
        )
        .annotate(week=TruncWeek("created_at"))
        .values("week")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("week")
    )

    # Monthly sales data - ALL sales
    monthly_sales_data = (
        Sales.objects.filter(
            created_at__range=[end_date - timedelta(days=365), end_date],
            status="completed"
        )
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("month")
    )

    # Annual sales data - ALL sales
    annual_sales_data = []
    for year_offset in range(3):
        year_end = end_date - timedelta(days=365*year_offset)
        year_start_date = year_end - timedelta(days=365)
        year_sales = Sales.objects.filter(
            created_at__range=[year_start_date, year_end],
            status="completed"
        ).aggregate(total=Sum("total_amount"), count=Count("id"))
        annual_sales_data.append({
            "year": year_end.year,
            "total": float(year_sales["total"] or Decimal("0.00")),
            "count": year_sales["count"] or 0
        })
    annual_sales_data.reverse()
    
    # Prepare period-based chart data
    if period == "daily":
        period_chart_labels = [item["date"].strftime("%b %d") for item in daily_sales_data]
        period_chart_data = [float(item["total"]) for item in daily_sales_data]
        period_chart_counts = [item["count"] for item in daily_sales_data]
    elif period == "weekly":
        period_chart_labels = [item["week"].strftime("%b %d") for item in weekly_sales_data]
        period_chart_data = [float(item["total"]) for item in weekly_sales_data]
        period_chart_counts = [item["count"] for item in weekly_sales_data]
    elif period == "monthly":
        period_chart_labels = [item["month"].strftime("%B %Y") for item in monthly_sales_data]
        period_chart_data = [float(item["total"]) for item in monthly_sales_data]
        period_chart_counts = [item["count"] for item in monthly_sales_data]
    else:  # annual
        period_chart_labels = [str(item["year"]) for item in annual_sales_data]
        period_chart_data = [item["total"] for item in annual_sales_data]
        period_chart_counts = [item["count"] for item in annual_sales_data]
    
    period_chart = {
        "labels": period_chart_labels,
        "datasets": [{
            "label": f"{period.capitalize()} Sales",
            "data": period_chart_data,
            "borderColor": "rgba(59, 130, 246, 1)",
                "backgroundColor": "rgba(59, 130, 246, 0.1)",
                "tension": 0.4,
            "fill": True
        }]
    }
    
    # Calculate period totals - ALL sales
    period_total = Sales.objects.filter(
        created_at__range=[period_start, end_date],
        status="completed"
    ).aggregate(total=Sum("total_amount"), count=Count("id"))
    
    prev_period_total = Sales.objects.filter(
        created_at__range=[prev_period_start, prev_period_end],
        status="completed"
    ).aggregate(total=Sum("total_amount"), count=Count("id"))
    
    period_revenue = float(period_total["total"] or Decimal("0.00"))
    period_transactions = period_total["count"] or 0
    prev_period_revenue = float(prev_period_total["total"] or Decimal("0.00"))
    prev_period_transactions = prev_period_total["count"] or 0
    
    period_growth = (
        ((period_revenue - prev_period_revenue) / prev_period_revenue * 100)
        if prev_period_revenue > 0
            else 0
        )

    # ========== RECENT ACTIVITY ==========
    # OPTIMIZED: Using select_related for cashier and seller, prefetch_related for items - ALL sales
    recent_sales = Sales.objects.filter(
        status="completed"
    ).select_related("cashier", "seller").prefetch_related("items", "items__product", "items__product__category").order_by("-created_at")[:5]

    # ========== PREPARE CONTEXT ==========
    context = {
        # Metric cards data
        "weekly_sales": {
            "value": float(weekly_sales_current),
            "growth": weekly_sales_growth,
            "growth_abs": abs(weekly_sales_growth),
            "trend": json.dumps(weekly_trend),
            "formatted": f"KSh {weekly_sales_current:,.0f}"
        },
        "new_users": {
            "value": new_users_current,
            "growth": new_users_growth,
            "growth_abs": abs(new_users_growth),
            "trend": json.dumps(new_users_trend),
            "formatted": f"{new_users_current:,}"
        },
        "purchase_orders": {
            "value": orders_current,
            "growth": orders_growth,
            "growth_abs": abs(orders_growth),
            "trend": json.dumps(orders_trend),
            "formatted": f"{orders_current:,}"
        },
        "products_sold": {
            "value": products_sold_current,
            "growth": products_sold_growth,
            "growth_abs": abs(products_sold_growth),
            "trend": json.dumps(products_trend),
            "formatted": f"{products_sold_current:,}"
        },
        # Charts data
        "category_pie_data": json.dumps(category_pie_data),
        "payment_chart_data": json.dumps(payment_chart_data),
        "monthly_bar_data": json.dumps(monthly_bar_data),
        "year_growth": year_growth,
        # Period-based data
        "period": period,
        "period_chart": json.dumps(period_chart),
        "period_revenue": period_revenue,
        "period_transactions": period_transactions,
        "period_growth": period_growth,
        "period_growth_abs": abs(period_growth),
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
        "year_growth_abs": abs(year_growth),
        # Recent activity
        "recent_sales": recent_sales,
    }

    # Use Tabler template by default, can switch with ?template=default
    template_name = request.GET.get("template", "analytics/dashboard_tabler.html")
    if template_name == "default":
        template_name = "analytics/dashboard.html"
    
    return render(request, template_name, context)


@login_required
def sales_report(request):
    """Detailed sales report with filtering options and period support."""
    if not (request.user.is_staff or request.user.role == "admin"):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("core:home")

    # Get filter parameters
    period = request.GET.get("period", "monthly")
    date_from = request.GET.get("start_date") or request.GET.get("date_from")
    date_to = request.GET.get("end_date") or request.GET.get("date_to")
    category = request.GET.get("category")
    seller = request.GET.get("seller")

    # Calculate date range based on period if not provided
    end_date = timezone.now()
    if not date_from or not date_to:
        if period == "daily":
            date_from = (end_date - timedelta(days=30)).date()
            date_to = end_date.date()
        elif period == "weekly":
            date_from = (end_date - timedelta(weeks=12)).date()
            date_to = end_date.date()
        elif period == "monthly":
            date_from = (end_date - timedelta(days=365)).date()
            date_to = end_date.date()
        else:  # annual
            date_from = (end_date - timedelta(days=365*3)).date()
            date_to = end_date.date()
    else:
        # Convert string dates to date objects
        from datetime import datetime
        if isinstance(date_from, str):
            date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        if isinstance(date_to, str):
            date_to = datetime.strptime(date_to, "%Y-%m-%d").date()

    # Base queryset - Use unified Sales model to track ALL sales - OPTIMIZED with select_related and prefetch_related
    sales = Sales.objects.filter(
        created_at__date__range=[date_from, date_to],
        status="completed"
    ).select_related("seller", "cashier").prefetch_related("items", "items__product", "items__product__category")

    # Apply filters
    if category:
        sales = sales.filter(items__product__category__name=category).distinct()
    if seller:
        sales = sales.filter(seller__username=seller)

    # Group by date for chart based on period
    if period == "daily":
        chart_data = (
            sales.annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(total=Sum("total_amount"))
            .order_by("date")
        )
        chart_labels = [item["date"].strftime("%b %d") for item in chart_data]
        chart_values = [float(item["total"]) for item in chart_data]
    elif period == "weekly":
        chart_data = (
            sales.annotate(week=TruncWeek("created_at"))
            .values("week")
            .annotate(total=Sum("total_amount"))
            .order_by("week")
        )
        chart_labels = [item["week"].strftime("%b %d") for item in chart_data]
        chart_values = [float(item["total"]) for item in chart_data]
    elif period == "monthly":
        chart_data = (
            sales.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Sum("total_amount"))
            .order_by("month")
        )
        chart_labels = [item["month"].strftime("%B %Y") for item in chart_data]
        chart_values = [float(item["total"]) for item in chart_data]
    else:  # annual
        chart_data = (
            sales.extra(select={"year": "EXTRACT(YEAR FROM created_at)"})
            .values("year")
            .annotate(total=Sum("total_amount"))
            .order_by("year")
        )
        chart_labels = [str(item["year"]) for item in chart_data]
        chart_values = [float(item["total"]) for item in chart_data]

    chart_data_json = {
        "labels": chart_labels,
        "datasets": [{
            "label": f"{period.capitalize()} Sales",
            "data": chart_values,
            "borderColor": "rgba(59, 130, 246, 1)",
            "backgroundColor": "rgba(59, 130, 246, 0.1)",
            "tension": 0.4,
            "fill": True
        }]
    }

    # Calculate summary statistics
    total_revenue = sales.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    total_transactions = sales.count()
    total_tax = sales.aggregate(total=Sum("tax_amount"))["total"] or Decimal("0.00")
    total_discounts = sales.aggregate(total=Sum("discount_amount"))["total"] or Decimal("0.00")
    avg_transaction = total_revenue / total_transactions if total_transactions > 0 else Decimal("0.00")
    
    # Calculate total items sold
    total_items = SalesItem.objects.filter(
        sale__created_at__date__range=[date_from, date_to],
        sale__status="completed"
    ).aggregate(total=Sum("quantity"))["total"] or 0
    
    # Calculate growth percentage (compare with previous period)
    if period == "daily":
        prev_start = date_from - timedelta(days=(date_to - date_from).days)
        prev_end = date_from - timedelta(days=1)
    elif period == "weekly":
        prev_start = date_from - timedelta(weeks=(date_to - date_from).days // 7)
        prev_end = date_from - timedelta(days=1)
    elif period == "monthly":
        prev_start = date_from - timedelta(days=(date_to - date_from).days)
        prev_end = date_from - timedelta(days=1)
    else:  # annual
        prev_start = date_from - timedelta(days=(date_to - date_from).days)
        prev_end = date_from - timedelta(days=1)
    
    prev_sales_total = Sales.objects.filter(
        created_at__date__range=[prev_start, prev_end],
        status="completed"
    ).aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    
    if prev_sales_total > 0:
        growth_percentage = ((total_revenue - prev_sales_total) / prev_sales_total) * 100
    else:
        growth_percentage = Decimal("0.00") if total_revenue == 0 else Decimal("100.00")

    # Top products - OPTIMIZED - ALL sales
    top_products = (
        SalesItem.objects.filter(
            sale__created_at__date__range=[date_from, date_to],
            sale__status="completed"
        )
        .select_related("product", "product__category", "sale")
        .values("product__name", "product__category__name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum("total_price")
        )
        .order_by("-total_quantity")[:10]
    )

    # Category breakdown - OPTIMIZED - ALL sales
    category_breakdown = (
        SalesItem.objects.filter(
            sale__created_at__date__range=[date_from, date_to],
            sale__status="completed"
        )
        .select_related("product", "product__category", "sale")
        .values("product__category__name")
        .annotate(
            total_revenue=Sum("total_price"),
            total_quantity=Sum("quantity")
        )
        .order_by("-total_revenue")
    )

    # Payment breakdown
    payment_breakdown = (
        sales.values("payment_method")
        .annotate(total=Sum("total_amount"), count=Count("id"))
        .order_by("-total")
    )

    # Paginate sales
    from django.core.paginator import Paginator
    paginator = Paginator(sales.order_by("-created_at"), 25)  # 25 items per page
    page_number = request.GET.get('page', 1)
    sales_page = paginator.get_page(page_number)
    
    context = {
        "period": period,
        "start_date": date_from.strftime("%Y-%m-%d"),
        "end_date": date_to.strftime("%Y-%m-%d"),
        "chart_data": json.dumps(chart_data_json),
        "sales": sales_page,  # Use paginated sales
        "categories": Category.objects.all().order_by("name"),
        "sellers": CustomUser.objects.filter(role="seller").order_by("username"),
        "date_from": date_from,
        "date_to": date_to,
        "category": category,
        "seller": seller,
        "total_sales": total_revenue,  # Alias for template compatibility
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "total_tax": total_tax,
        "total_discounts": total_discounts,
        "average_order": avg_transaction,  # Alias for template compatibility
        "avg_transaction": avg_transaction,
        "total_items": total_items,
        "growth_percentage": growth_percentage,
        "top_products": top_products,
        "category_breakdown": category_breakdown,
        "payment_breakdown": payment_breakdown,
    }

    # Use Tabler template by default
    template_name = request.GET.get("template", "analytics/sales_report_tabler.html")
    if template_name == "default":
        template_name = "analytics/sales_report.html"
    
    return render(request, template_name, context)


@login_required
def export_sales_data(request):
    """Export sales data to Excel with period support."""
    if not (request.user.is_staff or request.user.role == "admin"):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect("analytics:dashboard")

    try:
        import pandas as pd
        from openpyxl.styles import Font, PatternFill, Alignment
        import io

        # Get filter parameters
        period = request.GET.get("period", "monthly")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        
        # Calculate date range based on period if not provided
        end_date = timezone.now()
        if not date_from or not date_to:
            if period == "daily":
                date_from = (end_date - timedelta(days=30)).date()
                date_to = end_date.date()
            elif period == "weekly":
                date_from = (end_date - timedelta(weeks=12)).date()
                date_to = end_date.date()
            elif period == "monthly":
                date_from = (end_date - timedelta(days=365)).date()
                date_to = end_date.date()
            else:  # annual
                date_from = (end_date - timedelta(days=365*3)).date()
                date_to = end_date.date()

        # Base queryset - Use unified Sales model to track ALL sales - OPTIMIZED
        sales = Sales.objects.filter(
            created_at__date__range=[date_from, date_to],
            status="completed"
        ).select_related("seller", "cashier").prefetch_related("items", "items__product", "items__product__category")

        # Create DataFrame
        data = []
        for sale in sales:
            # Get all items for this sale
            items = sale.items.all()
            for item in items:
                data.append({
                    "Sale Number": sale.sale_number,
                    "Date": sale.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Customer": sale.customer_name or "Walk-in",
                    "Cashier": sale.cashier.get_full_name() or sale.cashier.username,
                    "Seller": sale.seller.get_full_name() if sale.seller else "N/A",
                    "Product": item.product.name,
                    "Category": item.product.category.name if item.product.category else "Uncategorized",
                    "Quantity": item.quantity,
                    "Unit Price": float(item.unit_price),
                    "Total Price": float(item.total_price),
                    "Payment Method": sale.payment_method,
                    "Subtotal": float(sale.subtotal),
                    "Tax": float(sale.tax_amount),
                    "Discount": float(sale.discount_amount),
                    "Total Amount": float(sale.total_amount),
                    "Status": sale.status,
                })

        df = pd.DataFrame(data)

        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Sales Data", index=False)
            
            # Get workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets["Sales Data"]
            
            # Style header row
            header_fill = PatternFill(start_color="16a34a", end_color="16a34a", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        output.seek(0)

        # Create HTTP response
        from django.http import HttpResponse
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="sales_report_{date_from}_{date_to}.xlsx"'
        return response

    except ImportError:
        messages.error(request, "Required libraries (pandas, openpyxl) not installed.")
        return redirect("analytics:sales_report")
    except Exception as e:
        messages.error(request, f"Error exporting data: {str(e)}")
        return redirect("analytics:sales_report")


@login_required
def seller_dashboard(request):
    """Seller-specific analytics dashboard."""
    if not (request.user.role == "seller" or request.user.is_staff):
        messages.error(request, "Access denied. Seller privileges required.")
        return redirect("core:home")

    # Get seller's sales - ALL sales (POS, e-commerce, manual)
    seller_sales = Sales.objects.filter(
        seller=request.user,
        status="completed"
    ).select_related("cashier").prefetch_related("items", "items__product", "items__product__category")

    # Calculate metrics
    total_sales = seller_sales.aggregate(total=Sum("total_amount"))["total"] or Decimal("0.00")
    total_transactions = seller_sales.count()
    avg_sale = total_sales / total_transactions if total_transactions > 0 else Decimal("0.00")
    
    # Commission calculation
    commission_rate = request.user.commission_rate or Decimal("0.00")
    total_commission = (total_sales * commission_rate) / 100

    # Recent sales
    recent_sales = seller_sales.order_by("-created_at")[:10]

    # Top products sold by this seller - ALL sales
    top_products = (
        SalesItem.objects.filter(
            sale__seller=request.user,
            sale__status="completed"
        )
        .select_related("product", "product__category", "sale")
        .values("product__name", "product__category__name")
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum("total_price")
        )
        .order_by("-total_quantity")[:10]
    )

    context = {
        "total_sales": total_sales,
        "total_transactions": total_transactions,
        "avg_sale": avg_sale,
        "commission_rate": commission_rate,
        "total_commission": total_commission,
        "recent_sales": recent_sales,
        "top_products": top_products,
    }

    return render(request, "analytics/seller_dashboard.html", context)

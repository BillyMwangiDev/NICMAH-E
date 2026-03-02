"""
Core views for NICMAH application.
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.utils import OperationalError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from catalog.models import Product
from pos.models import POSSaleItem
from orders.models import OrderItem
from .models import SiteSettings


def home(request):
    """Home page view."""
    try:
        site_settings = SiteSettings.objects.get(site_id=1)
    except SiteSettings.DoesNotExist:
        site_settings = None

    context = {
        "site_settings": site_settings,
        "page_title": "Home",
    }
    return render(request, "core/home.html", context)


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint for production monitoring."""
    try:
        # Test database connection
        connection.ensure_connection()
        db_status = "healthy"
    except OperationalError:
        db_status = "unhealthy"

    health_data = {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "timestamp": "2025-09-04T12:00:00Z"
    }

    status_code = 200 if health_data["status"] == "healthy" else 503
    return JsonResponse(health_data, status=status_code)


def get_featured_products(start_date, end_date, limit=8):
    """
    Get featured products based on sales performance and stock availability.
    Prioritizes products with:
    1. High sales volume in recent period
    2. Available stock
    3. Good profit margins
    """
    # Get products with sales in the period
    products_with_sales = Product.objects.filter(
        Q(possaleitem__sale__created_at__range=[start_date, end_date]) |
        Q(orderitem__order__created_at__range=[start_date, end_date])
    ).distinct()
    
    # Annotate with sales data
    featured_products = products_with_sales.annotate(
        # POS sales
        pos_quantity=Sum('possaleitem__quantity', 
                         filter=Q(possaleitem__sale__created_at__range=[start_date, end_date],
                                 possaleitem__sale__status='completed')),
        pos_revenue=Sum('possaleitem__total_price',
                       filter=Q(possaleitem__sale__created_at__range=[start_date, end_date],
                               possaleitem__sale__status='completed')),
        # Online orders
        order_quantity=Sum('orderitem__quantity',
                          filter=Q(orderitem__order__created_at__range=[start_date, end_date],
                                  orderitem__order__status__in=['confirmed', 'completed'])),
        order_revenue=Sum('orderitem__total_price',
                         filter=Q(orderitem__order__created_at__range=[start_date, end_date],
                                 orderitem__order__status__in=['confirmed', 'completed'])),
    ).filter(
        # Only include products with stock available
        stock_quantity__gt=0,
        is_active=True,
        is_available=True
    )
    
    # Calculate total sales for each product
    for product in featured_products:
        product.total_quantity = (product.pos_quantity or 0) + (product.order_quantity or 0)
        product.total_revenue = (product.pos_revenue or 0) + (product.order_revenue or 0)
    
    # Sort by total quantity sold (most selling first)
    featured_products = sorted(
        featured_products, 
        key=lambda x: x.total_quantity, 
        reverse=True
    )[:limit]
    
    # If we don't have enough products with sales, add popular products with stock
    if len(featured_products) < limit:
        remaining_limit = limit - len(featured_products)
        
        # First try to get featured products
        additional_products = Product.objects.filter(
            stock_quantity__gt=0,
            is_active=True,
            is_available=True,
            is_featured=True
        ).exclude(
            id__in=[p.id for p in featured_products]
        )[:remaining_limit]
        
        featured_products.extend(additional_products)
        
        # If still not enough, add any products with stock
        if len(featured_products) < limit:
            final_remaining = limit - len(featured_products)
            more_products = Product.objects.filter(
                stock_quantity__gt=0,
                is_active=True,
                is_available=True
            ).exclude(
                id__in=[p.id for p in featured_products]
            ).order_by('-stock_quantity')[:final_remaining]
            
            featured_products.extend(more_products)
    
    return featured_products


def about(request):
    """
    About page view.
    """
    context = {
        "page_title": "About Us",
    }
    return render(request, "core/about.html", context)


def contact(request):
    """
    Contact page view.
    """
    context = {
        "page_title": "Contact Us",
    }
    return render(request, "core/contact.html", context)
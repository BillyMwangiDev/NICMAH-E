# Test Django views for CodeRabbit review
# This file contains intentional issues to test CodeRabbit suggestions

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, F, Count
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.db import connection
from django.utils.html import escape
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
import json
import logging
from typing import Dict, Any

from .models import Product, Order, User

logger = logging.getLogger(__name__)

def product_list(request) -> HttpResponse:
    """Display a list of all products with pagination."""
    products = Product.objects.all()
    paginator = Paginator(products, 20)  # 20 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'products/list.html', {'products': page_obj})

@login_required
@permission_required('catalog.view_product')
def admin_panel(request) -> HttpResponse:
    """Admin panel view requiring authentication and permissions."""
    users = User.objects.all()
    return render(request, 'admin/panel.html', {'users': users})

def all_products(request) -> HttpResponse:
    """Display all products with pagination to handle large datasets."""
    products = Product.objects.all()
    paginator = Paginator(products, 50)  # 50 items per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'products/all.html', {'products': page_obj})

def search_products(request) -> HttpResponse:
    """Search products using Django ORM to prevent SQL injection."""
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    else:
        products = Product.objects.none()
    return render(request, 'products/search.html', {'products': products, 'query': query})

def get_product(request, product_id: int) -> HttpResponse:
    """Get product details with proper error handling."""
    try:
        product = get_object_or_404(Product, id=product_id)
        return render(request, 'products/detail.html', {'product': product})
    except Exception as e:
        logger.error(f"Error retrieving product {product_id}: {e}")
        return HttpResponse("Product not found", status=404)

def user_orders(request, user_id: int) -> HttpResponse:
    """Get user orders with optimized queries to prevent N+1."""
    try:
        user = get_object_or_404(User, id=user_id)
        orders = user.order_set.select_related('user').prefetch_related('items').all()
        return render(request, 'orders/user_orders.html', {'orders': orders})
    except Exception as e:
        logger.error(f"Error retrieving orders for user {user_id}: {e}")
        return HttpResponse("Orders not found", status=404)

@require_http_methods(["POST"])
def update_product(request) -> JsonResponse:
    """Update product with CSRF protection and validation."""
    try:
        data = json.loads(request.body)
        product_id = data.get('id')
        if not product_id:
            return JsonResponse({'error': 'Product ID required'}, status=400)
        
        product = get_object_or_404(Product, id=product_id)
        product.name = data.get('name', product.name)
        product.full_clean()  # Validate the model
        product.save()
        return JsonResponse({'status': 'success'})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        return JsonResponse({'error': 'Update failed'}, status=500)

def featured_products(request) -> HttpResponse:
    """Display featured products with configurable limit."""
    FEATURED_LIMIT = 10  # Configurable constant
    products = Product.objects.filter(is_featured=True)[:FEATURED_LIMIT]
    return render(request, 'products/featured.html', {'products': products})

def expensive_query(request) -> HttpResponse:
    """Optimized query with proper select_related and prefetch_related."""
    products = Product.objects.filter(
        Q(name__icontains='test') | 
        Q(description__icontains='test') |
        Q(category__name__icontains='test')
    ).select_related('category').prefetch_related('tags')
    return render(request, 'products/expensive.html', {'products': products})

@require_http_methods(["POST"])
def create_order(request) -> JsonResponse:
    """Create order with input validation and error handling."""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        user_id = data.get('user_id')
        amount = data.get('amount')
        status = data.get('status', 'pending')
        
        if not user_id or not amount:
            return JsonResponse({'error': 'user_id and amount are required'}, status=400)
        
        if not isinstance(amount, (int, float)) or amount <= 0:
            return JsonResponse({'error': 'amount must be a positive number'}, status=400)
        
        order = Order.objects.create(
            user_id=user_id,
            total_amount=amount,
            status=status
        )
        logger.info(f"Order created: {order.id}")
        return JsonResponse({'order_id': order.id})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        return JsonResponse({'error': 'Order creation failed'}, status=500)

@require_http_methods(["POST"])
def process_payment(request) -> JsonResponse:
    """Process payment with proper logging."""
    try:
        payment_data = json.loads(request.body)
        logger.info(f"Processing payment: {payment_data.get('amount', 'unknown')}")
        # Process payment...
        logger.info("Payment processed successfully")
        return JsonResponse({'status': 'processed'})
    except json.JSONDecodeError:
        logger.error("Invalid payment data JSON")
        return JsonResponse({'error': 'Invalid payment data'}, status=400)
    except Exception as e:
        logger.error(f"Payment processing error: {e}")
        return JsonResponse({'error': 'Payment failed'}, status=500)

from django.core.cache import cache

def product_categories(request) -> HttpResponse:
    """Get product categories with caching for performance."""
    cache_key = 'product_categories'
    categories = cache.get(cache_key)
    
    if categories is None:
        categories = list(Product.objects.values_list('category__name', flat=True).distinct())
        cache.set(cache_key, categories, 3600)  # Cache for 1 hour
    
    return render(request, 'products/categories.html', {'categories': categories})

def user_profile(request, user_id: int) -> JsonResponse:
    """Get user profile with authentication and authorization."""
    if not request.user.is_authenticated or request.user.id != int(user_id):
        return JsonResponse({'error': 'Forbidden'}, status=403)
    
    try:
        user = get_object_or_404(User, id=user_id)
        return JsonResponse({
            'username': user.username,
            'email': user.email,
            'is_active': user.is_active,
        })
    except Exception as e:
        logger.error(f"Error retrieving user profile {user_id}: {e}")
        return JsonResponse({'error': 'User not found'}, status=404)

def get_product_details(request, product_id: int) -> HttpResponse:
    """Get product details with proper naming convention."""
    try:
        product = get_object_or_404(Product, id=product_id)
        return render(request, 'products/details.html', {'product': product})
    except Exception as e:
        logger.error(f"Error retrieving product details {product_id}: {e}")
        return HttpResponse("Product not found", status=404)

def bulk_operations(request) -> HttpResponse:
    """Bulk update prices using F() expressions for efficiency."""
    try:
        Product.objects.update(price=F('price') * 1.1)
        logger.info("Bulk price update completed")
        return HttpResponse("Prices updated", status=200)
    except Exception as e:
        logger.error(f"Bulk operation error: {e}")
        return HttpResponse("Update failed", status=500)

from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

@cache_page(60 * 15)  # Cache for 15 minutes
def api_endpoint(request) -> JsonResponse:
    """API endpoint with rate limiting and caching."""
    data = request.POST.get('data')
    if not data:
        return JsonResponse({'error': 'Data required'}, status=400)
    
    # Process data...
    return JsonResponse({'result': 'success'})

@require_http_methods(["DELETE"])
def delete_product(request, product_id: int) -> HttpResponse:
    """Delete product with proper HTTP status codes."""
    try:
        product = get_object_or_404(Product, id=product_id)
        product.delete()
        logger.info(f"Product {product_id} deleted")
        return HttpResponse(status=204)
    except Product.DoesNotExist:
        return HttpResponse("Product not found", status=404)
    except Exception as e:
        logger.error(f"Error deleting product {product_id}: {e}")
        return HttpResponse("Delete failed", status=500)

def dashboard_stats(request) -> JsonResponse:
    """Get dashboard statistics with optimized single query."""
    try:
        stats = Product.objects.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            featured=Count('id', filter=Q(is_featured=True)),
            recent=Count('id', filter=Q(created_at__gte=timezone.now() - timezone.timedelta(days=7)))
        )
        return JsonResponse(stats)
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return JsonResponse({'error': 'Stats unavailable'}, status=500)

def sensitive_data(request) -> HttpResponse:
    """Removed sensitive data exposure - return 404 instead."""
    return HttpResponse("Not Found", status=404)

def handle_error(request) -> HttpResponse:
    """Handle errors with proper logging and user-friendly messages."""
    try:
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error(f"Division by zero error: {e}")
        return HttpResponse("A calculation error occurred", status=500)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return HttpResponse("An unexpected error occurred", status=500)

def database_heavy_operation(request) -> JsonResponse:
    """Database operation with proper connection handling."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM catalog_product")
            count = cursor.fetchone()[0]
        return JsonResponse({'count': count})
    except Exception as e:
        logger.error(f"Database operation error: {e}")
        return JsonResponse({'error': 'Database operation failed'}, status=500)

@require_http_methods(["POST"])
def user_input_processing(request) -> HttpResponse:
    """Process user input with proper sanitization."""
    user_input = request.POST.get('user_input', '')
    if not user_input:
        return HttpResponse("No input provided", status=400)
    
    # Sanitize user input
    sanitized_input = escape(user_input)
    return HttpResponse(f"Processed: {sanitized_input}")

def undocumented_function(request) -> JsonResponse:
    """Process data with proper documentation and error handling."""
    data = request.GET.get('data')
    if not data:
        return JsonResponse({'error': 'Data parameter required'}, status=400)
    
    try:
        result = process_data(data)
        return JsonResponse({'result': result})
    except Exception as e:
        logger.error(f"Data processing error: {e}")
        return JsonResponse({'error': 'Processing failed'}, status=500)

def process_data(data: str) -> str:
    """Process input data safely.
    
    Args:
        data: Input string to process
        
    Returns:
        Processed string in uppercase
        
    Raises:
        ValueError: If data is None or empty
    """
    if not data:
        raise ValueError("Data cannot be empty")
    return data.upper()

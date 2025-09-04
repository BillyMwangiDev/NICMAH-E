# Test Django views for CodeRabbit review
# This file contains intentional issues to test CodeRabbit suggestions

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.db import connection
import json
import logging

from .models import Product, Order, User

logger = logging.getLogger(__name__)

# Missing docstring and type hints
def product_list(request):
    # No docstring
    products = Product.objects.all()
    return render(request, 'products/list.html', {'products': products})

# Security issue - no authentication required
def admin_panel(request):
    # Should require authentication
    users = User.objects.all()
    return render(request, 'admin/panel.html', {'users': users})

# Performance issue - no pagination
def all_products(request):
    products = Product.objects.all()  # Could be thousands of products
    return render(request, 'products/all.html', {'products': products})

# Security issue - SQL injection
def search_products(request):
    query = request.GET.get('q', '')
    # Vulnerable to SQL injection
    products = Product.objects.raw(f"SELECT * FROM catalog_product WHERE name LIKE '%{query}%'")
    return render(request, 'products/search.html', {'products': products})

# Bad practice - no error handling
def get_product(request, product_id):
    product = Product.objects.get(id=product_id)  # No try-catch
    return render(request, 'products/detail.html', {'product': product})

# Performance issue - N+1 queries
def user_orders(request, user_id):
    user = User.objects.get(id=user_id)
    orders = user.order_set.all()
    for order in orders:
        # This will cause N+1 queries
        print(f"Order {order.id} has {order.items.count()} items")
    return render(request, 'orders/user_orders.html', {'orders': orders})

# Security issue - no CSRF protection
@csrf_exempt
def update_product(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        product_id = data.get('id')
        product = Product.objects.get(id=product_id)
        product.name = data.get('name')
        product.save()
        return JsonResponse({'status': 'success'})

# Bad practice - hardcoded values
def featured_products(request):
    products = Product.objects.filter(is_featured=True)[:10]  # Magic number
    return render(request, 'products/featured.html', {'products': products})

# Performance issue - inefficient query
def expensive_query(request):
    # This query could be optimized
    products = Product.objects.filter(
        Q(name__icontains='test') | 
        Q(description__icontains='test') |
        Q(category__name__icontains='test')
    ).select_related('category').prefetch_related('tags')
    return render(request, 'products/expensive.html', {'products': products})

# Security issue - no input validation
def create_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # No validation of input data
        order = Order.objects.create(
            user_id=data.get('user_id'),
            total_amount=data.get('amount'),
            status=data.get('status')
        )
        return JsonResponse({'order_id': order.id})

# Bad practice - no logging
def process_payment(request):
    # No logging of payment processing
    payment_data = json.loads(request.body)
    # Process payment...
    return JsonResponse({'status': 'processed'})

# Performance issue - no caching
def product_categories(request):
    categories = Product.objects.values_list('category__name', flat=True).distinct()
    # Should use caching for this query
    return render(request, 'products/categories.html', {'categories': categories})

# Security issue - sensitive data exposure
def user_profile(request, user_id):
    user = User.objects.get(id=user_id)
    # Exposing sensitive information
    return JsonResponse({
        'username': user.username,
        'email': user.email,
        'password_hash': user.password,  # Should not expose this
        'is_active': user.is_active
    })

# Bad practice - inconsistent naming
def GetProductDetails(request, product_id):  # Should be snake_case
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'products/details.html', {'product': product})

# Performance issue - no database optimization
def bulk_operations(request):
    # This could be optimized with bulk operations
    products = Product.objects.all()
    for product in products:
        product.price = product.price * 1.1  # 10% increase
        product.save()  # Individual saves instead of bulk_update
    return HttpResponse("Prices updated")

# Security issue - no rate limiting
def api_endpoint(request):
    # No rate limiting protection
    data = request.POST.get('data')
    # Process data...
    return JsonResponse({'result': 'success'})

# Bad practice - no proper HTTP status codes
def delete_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        product.delete()
        return HttpResponse("Product deleted")  # Should return proper status code
    except Product.DoesNotExist:
        return HttpResponse("Product not found")  # Should return 404

# Performance issue - unnecessary database queries
def dashboard_stats(request):
    # Multiple separate queries instead of one optimized query
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    featured_products = Product.objects.filter(is_featured=True).count()
    recent_products = Product.objects.filter(created_at__gte=timezone.now() - timezone.timedelta(days=7)).count()
    
    return JsonResponse({
        'total': total_products,
        'active': active_products,
        'featured': featured_products,
        'recent': recent_products
    })

# Security issue - no proper authentication
def sensitive_data(request):
    # No authentication check
    if request.user.is_authenticated:
        # Still not checking permissions
        data = {
            'secret_key': 'super-secret-key',
            'admin_password': 'admin123',
            'database_url': 'postgresql://user:pass@localhost/db'
        }
        return JsonResponse(data)
    return HttpResponse("Unauthorized", status=401)

# Bad practice - no proper error messages
def handle_error(request):
    try:
        result = 1 / 0
    except Exception as e:
        # Generic error message
        return HttpResponse("An error occurred")

# Performance issue - no connection pooling
def database_heavy_operation(request):
    # This could benefit from connection pooling
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM catalog_product")
        count = cursor.fetchone()[0]
    return JsonResponse({'count': count})

# Security issue - no input sanitization
def user_input_processing(request):
    user_input = request.POST.get('user_input')
    # No sanitization of user input
    return HttpResponse(f"Processed: {user_input}")

# Bad practice - no proper documentation
def undocumented_function(request):
    # No docstring explaining what this function does
    data = request.GET.get('data')
    result = process_data(data)
    return JsonResponse({'result': result})

def process_data(data):
    # No docstring
    return data.upper() if data else ""

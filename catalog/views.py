from django.shortcuts import render, get_object_or_404
from django.db.models import Q, F
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponseForbidden
from .models import Product, Category

def is_admin_user(request):
    """Check if the current user is an authenticated admin/staff user."""
    return request.user.is_authenticated and request.user.is_staff


def product_list(request):
    """
    Enhanced product list with advanced search functionality.
    """
    # Get search parameters
    query = request.GET.get("q", "")
    category_filter = request.GET.get("category", "")
    price_min = request.GET.get("price_min", "")
    price_max = request.GET.get("price_max", "")
    stock_filter = request.GET.get("stock", "")
    sort_by = request.GET.get("sort", "name")
    
    # Base queryset
    products = Product.objects.filter(is_active=True, is_available=True)
    
    # Exclude admin-only category products for non-admin users
    if not is_admin_user(request):
        products = products.filter(category__is_admin_only=False)
    
    # Apply search filters
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    # Category filter
    if category_filter:
        category_obj = Category.objects.filter(slug=category_filter, is_active=True).first()
        # Check if trying to access admin-only category without admin privileges
        if category_obj and category_obj.is_admin_only:
            if not is_admin_user(request):
                # Reset category filter if user is not admin
                category_filter = ""
            else:
                products = products.filter(category__slug=category_filter)
        elif category_obj:
            products = products.filter(category__slug=category_filter)
    
    # Price range filter
    if price_min:
        try:
            products = products.filter(price__gte=float(price_min))
        except ValueError:
            pass
    
    if price_max:
        try:
            products = products.filter(price__lte=float(price_max))
        except ValueError:
            pass
    
    # Stock filter
    if stock_filter == "in_stock":
        products = products.filter(stock_quantity__gt=0)
    elif stock_filter == "low_stock":
        products = products.filter(
            stock_quantity__gt=0,
            stock_quantity__lte=F('min_stock_level')
        )
    elif stock_filter == "out_of_stock":
        products = products.filter(stock_quantity=0)
    
    # Sorting
    if sort_by == "name":
        products = products.order_by("name")
    elif sort_by == "name_desc":
        products = products.order_by("-name")
    elif sort_by == "price":
        products = products.order_by("price")
    elif sort_by == "price_desc":
        products = products.order_by("-price")
    elif sort_by == "stock":
        products = products.order_by("-stock_quantity")
    elif sort_by == "newest":
        products = products.order_by("-created_at")
    elif sort_by == "featured":
        products = products.order_by("-is_featured", "name")
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter dropdown (exclude admin-only for non-admin users)
    categories = Category.objects.filter(is_active=True)
    if not is_admin_user(request):
        categories = categories.filter(is_admin_only=False)
    categories = categories.order_by("name")
    
    # Get search suggestions based on query
    search_suggestions = []
    if query and len(query) >= 2:
        products_qs = Product.objects.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        ).filter(is_active=True, is_available=True)
        
        # Exclude admin-only category products for non-admin users
        if not is_admin_user(request):
            products_qs = products_qs.filter(category__is_admin_only=False)
        
        search_suggestions = list(products_qs.values_list('name', flat=True)[:5])
    
    context = {
        "products": page_obj,
        "categories": categories,
        "query": query,
        "category_filter": category_filter,
        "price_min": price_min,
        "price_max": price_max,
        "stock_filter": stock_filter,
        "sort_by": sort_by,
        "search_suggestions": search_suggestions,
        "total_products": products.count(),
        "filters_applied": any([query, category_filter, price_min, price_max, stock_filter]),
    }
    return render(request, "catalog/product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Check if product belongs to admin-only category and user is not admin
    if product.category.is_admin_only and not is_admin_user(request):
        return HttpResponseForbidden("Access denied. This product is only available to admin users.")
    
    related_products = Product.objects.filter(category=product.category, is_active=True).exclude(id=product.id)
    # Exclude admin-only category products for non-admin users
    if not is_admin_user(request):
        related_products = related_products.filter(category__is_admin_only=False)
    related_products = related_products[:4]
    context = {
        "product": product,
        "related_products": related_products,
    }
    return render(request, "catalog/product_detail.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Check if category is admin-only and user is not admin
    if category.is_admin_only and not is_admin_user(request):
        return HttpResponseForbidden("Access denied. This category is only available to admin users.")
    
    products = category.products.filter(is_active=True)
    context = {
        "category": category,
        "products": products,
    }
    return render(request, "catalog/category_detail.html", context)


def search_suggestions(request):
    """
    AJAX endpoint for search suggestions.
    """
    
    query = request.GET.get("q", "")
    if len(query) < 2:
        return JsonResponse({"suggestions": []})
    
    # Get product suggestions
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(sku__icontains=query) |
        Q(category__name__icontains=query)
    ).filter(is_active=True, is_available=True)
    
    # Exclude admin-only category products for non-admin users
    if not is_admin_user(request):
        products = products.filter(category__is_admin_only=False)
    
    products = products[:10]
    
    suggestions = []
    for product in products:
        suggestions.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "category": product.category.name,
            "price": float(product.price),
            "stock": product.stock_quantity,
            "url": product.get_absolute_url(),
        })
    
    return JsonResponse({"suggestions": suggestions})


def quick_search(request):
    """
    Quick search functionality for homepage.
    """
    query = request.GET.get("q", "")
    if not query:
        return render(request, "catalog/quick_search.html", {"products": []})
    
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(sku__icontains=query) |
        Q(category__name__icontains=query)
    ).filter(is_active=True, is_available=True)
    
    # Exclude admin-only category products for non-admin users
    if not is_admin_user(request):
        products = products.filter(category__is_admin_only=False)
    
    products = products.order_by("-is_featured", "name")[:20]
    
    context = {
        "products": products,
        "query": query,
        "total_results": products.count(),
    }
    return render(request, "catalog/quick_search.html", context)


def api_product_search(request):
    """
    API endpoint for product search used by receipt generation.
    Returns JSON data for product selection.
    Rate limited and protected against abuse.
    """
    # Rate limiting check (basic implementation)
    from django.core.cache import cache
    from django.conf import settings
    
    client_ip = request.META.get('REMOTE_ADDR', 'unknown')
    rate_limit_key = f"api_search:{client_ip}"
    request_count = cache.get(rate_limit_key, 0)
    
    max_requests = settings.API_RATE_LIMIT
    if request_count >= max_requests:
        return JsonResponse(
            {"error": "Rate limit exceeded. Please try again later."},
            status=429
        )
    
    cache.set(rate_limit_key, request_count + 1, 60)  # 1 minute window
    
    query = request.GET.get("q", "")
    if len(query) < 1:
        return JsonResponse({"products": []})
    
    # Input validation - prevent SQL injection and XSS
    if len(query) > 100:  # Limit query length
        return JsonResponse({"error": "Query too long"}, status=400)
    
    # Get products matching the search query
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(sku__icontains=query) |
        Q(category__name__icontains=query)
    ).filter(is_active=True, is_available=True)
    
    # Exclude admin-only category products for non-admin users
    if not is_admin_user(request):
        products = products.filter(category__is_admin_only=False)
    
    products = products.order_by("name")[:20]
    
    product_list = []
    for product in products:
        product_list.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "category": product.category.name if product.category else "",
            "price": float(product.price),
            "stock": product.stock_quantity,
            "unit": "piece",
            "description": product.description[:100] if product.description else "",
        })
    
    # Return both formats for compatibility
    return JsonResponse({
        "products": product_list,
        "data": product_list  # Alternative format
    })

"""
Common utility functions to eliminate duplicate code across the project.
"""

import uuid
import random
import string
from decimal import Decimal
from django.utils import timezone
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse


def generate_unique_id():
    """Generate a unique identifier."""
    return str(uuid.uuid4())


def generate_random_string(length=8):
    """Generate a random string of specified length."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def generate_slug(text, model_class=None, field_name="slug"):
    """Generate a unique slug from text."""
    base_slug = slugify(text)
    if not model_class:
        return base_slug

    slug = base_slug
    counter = 1

    while model_class.objects.filter(**{field_name: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def format_currency(amount, currency="USD"):
    """Format amount as currency."""
    if amount is None:
        return f"0.00 {currency}"

    try:
        amount = Decimal(str(amount))
        return f"{amount:.2f} {currency}"
    except (ValueError, TypeError):
        return f"0.00 {currency}"


def calculate_percentage(part, total):
    """Calculate percentage."""
    if not total or total == 0:
        return 0
    return (part / total) * 100


def calculate_discount(original_price, discount_percentage):
    """Calculate discounted price."""
    if not discount_percentage or discount_percentage <= 0:
        return original_price

    discount_amount = (original_price * discount_percentage) / 100
    return original_price - discount_amount


def calculate_tax(amount, tax_rate):
    """Calculate tax amount."""
    if not tax_rate or tax_rate <= 0:
        return Decimal("0.00")

    return (amount * tax_rate) / 100


def get_date_range(days=30):
    """Get date range for the last N days."""
    end_date = timezone.now()
    start_date = end_date - timezone.timedelta(days=days)
    return start_date, end_date


def paginate_queryset(request, queryset, per_page=20):
    """Paginate a queryset."""
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return page_obj


def search_queryset(queryset, search_term, search_fields):
    """Search a queryset across multiple fields."""
    if not search_term:
        return queryset

    query = Q()
    for field in search_fields:
        if hasattr(queryset.model, field):
            query |= Q(**{f"{field}__icontains": search_term})

    return queryset.filter(query)


def filter_queryset(queryset, filters):
    """Filter a queryset based on filter parameters."""
    for field, value in filters.items():
        if value and hasattr(queryset.model, field):
            if isinstance(value, list):
                queryset = queryset.filter(**{f"{field}__in": value})
            else:
                queryset = queryset.filter(**{field: value})

    return queryset


def ajax_response(data, success=True, message="", status=200):
    """Return standardized AJAX response."""
    response_data = {"success": success, "message": message, "data": data}
    return JsonResponse(response_data, status=status)


def ajax_error(message, status=400):
    """Return standardized AJAX error response."""
    return ajax_response({}, success=False, message=message, status=status)


def ajax_success(data, message="Success"):
    """Return standardized AJAX success response."""
    return ajax_response(data, success=True, message=message)


def validate_file_extension(filename, allowed_extensions):
    """Validate file extension."""
    import os

    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def validate_file_size(file, max_size_mb):
    """Validate file size."""
    max_size_bytes = max_size_mb * 1024 * 1024
    return file.size <= max_size_bytes


def get_file_size_display(size_bytes):
    """Convert bytes to human readable format."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def generate_order_number():
    """Generate a unique order number."""
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    random_suffix = generate_random_string(4)
    return f"ORD-{timestamp}-{random_suffix}"


def generate_receipt_number():
    """Generate a unique receipt number."""
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    random_suffix = generate_random_string(4)
    return f"RCP-{timestamp}-{random_suffix}"


def calculate_stock_value(products):
    """Calculate total stock value."""
    total_value = Decimal("0.00")
    for product in products:
        if product.stock_quantity and product.price:
            total_value += product.stock_quantity * product.price
    return total_value


def get_low_stock_products(products, threshold=10):
    """Get products with low stock."""
    return [product for product in products if product.stock_quantity <= threshold]


def format_phone_number(phone):
    """Format phone number for display."""
    if not phone:
        return ""

    # Remove all non-digit characters
    digits = "".join(filter(str.isdigit, str(phone)))

    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == "1":
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone


def sanitize_filename(filename):
    """Sanitize filename for safe storage."""
    import re

    # Remove or replace unsafe characters
    filename = re.sub(r"[^\w\s-]", "", filename)
    filename = re.sub(r"[-\s]+", "-", filename)
    return filename.strip("-").lower()


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def is_mobile_device(request):
    """Check if request is from mobile device."""
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
    mobile_agents = ["mobile", "android", "iphone", "ipad", "blackberry"]
    return any(agent in user_agent for agent in mobile_agents)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
import json

from .models import Cart, CartItem, Order, OrderItem
from catalog.models import Product


def cart_view(request):
    """Display cart page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_amount': cart.total_amount,
        'item_count': cart.item_count,
    }
    return render(request, 'orders/cart.html', context)


@login_required
def checkout_view(request):
    """Checkout page"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.all()
    
    if request.method == 'POST':
        # Process checkout
        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')
        customer_email = request.POST.get('customer_email')
        shipping_address = request.POST.get('shipping_address')
        notes = request.POST.get('notes', '')
        
        if not all([customer_name, customer_phone, customer_email, shipping_address]):
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'orders/checkout.html', {'cart': cart, 'cart_items': cart_items})
        
        # Create order
        order = Order.objects.create(
            customer=request.user,
            total_amount=cart.total_amount,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            shipping_address=shipping_address,
            notes=notes
        )
        
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                product_name=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price
            )
        
        # Clear cart
        cart.delete()
        
        messages.success(request, f'Order {order.order_number} created successfully!')
        return redirect('orders:order_detail', order_id=order.id)
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_amount': cart.total_amount,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_detail(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def my_orders(request):
    """User's order history"""
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    return render(request, 'orders/my_orders.html', {'orders': orders})


# Helper function to get or create cart
def get_or_create_cart(request):
    """Get or create cart for user/session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            defaults={'expires_at': timezone.now() + timedelta(days=7)}
        )
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        cart, created = Cart.objects.get_or_create(
            session_key=session_key,
            defaults={'expires_at': timezone.now() + timedelta(days=7)}
        )
    
    return cart


# API Views for AJAX cart operations
@csrf_exempt
@require_http_methods(["POST"])
def api_add_to_cart(request):
    """API endpoint to add item to cart"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Product ID is required'})
        
        product = get_object_or_404(Product, id=product_id)
        cart = get_or_create_cart(request)
        
        # Check if item already exists in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity, 'unit_price': product.price}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_count': cart.item_count,
            'cart_total': float(cart.total_amount)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def api_remove_from_cart(request):
    """API endpoint to remove item from cart"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Product ID is required'})
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        product_name = cart_item.product.name
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{product_name} removed from cart',
            'cart_count': cart.item_count,
            'cart_total': float(cart.total_amount)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def api_update_cart_quantity(request):
    """API endpoint to update item quantity in cart"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Product ID is required'})
        
        if quantity <= 0:
            return JsonResponse({'success': False, 'error': 'Quantity must be greater than 0'})
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        cart_item.quantity = quantity
        cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Quantity updated for {cart_item.product.name}',
            'cart_count': cart.item_count,
            'cart_total': float(cart.total_amount),
            'item_total': float(cart_item.total_price)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@require_http_methods(["POST"])
def api_clear_cart(request):
    """API endpoint to clear cart"""
    try:
        cart = get_or_create_cart(request)
        cart.items.all().delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart cleared successfully',
            'cart_count': 0,
            'cart_total': 0.0
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_http_methods(["GET"])
def api_get_cart(request):
    """API endpoint to get cart contents"""
    try:
        cart = get_or_create_cart(request)
        items = []
        
        for item in cart.items.all():
            items.append({
                'id': item.id,
                'product_id': item.product.id,
                'product_name': item.product.name,
                'product_image': item.product.main_image.url if item.product.main_image else None,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price),
                'sku': item.product.sku
            })
        
        return JsonResponse({
            'success': True,
            'items': items,
            'cart_count': cart.item_count,
            'cart_total': float(cart.total_amount)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

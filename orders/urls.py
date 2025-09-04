from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('my-orders/', views.my_orders, name='my_orders'),
    
    # API endpoints for cart operations
    path('api/cart/add/', views.api_add_to_cart, name='api_add_to_cart'),
    path('api/cart/remove/', views.api_remove_from_cart, name='api_remove_from_cart'),
    path('api/cart/update/', views.api_update_cart_quantity, name='api_update_cart_quantity'),
    path('api/cart/clear/', views.api_clear_cart, name='api_clear_cart'),
    path('api/cart/get/', views.api_get_cart, name='api_get_cart'),
]

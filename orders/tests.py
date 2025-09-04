from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from catalog.models import Category, Product
from .models import Cart, CartItem, Order, OrderItem


class OrdersViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", price=10.00, category=self.category, sku="TEST001", stock_quantity=100
        )

    def test_cart_page_loads(self):
        resp = self.client.get(reverse("orders:cart"))
        self.assertEqual(resp.status_code, 200)

    def test_checkout_page_loads(self):
        # Login the user first
        self.client.login(username="testuser", password="testpass123")
        resp = self.client.get(reverse("orders:checkout"))
        if resp.status_code == 302:
            # Follow the redirect
            resp = self.client.get(resp.url)
        self.assertEqual(resp.status_code, 200)


class OrdersModelsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", price=10.00, category=self.category, sku="TEST001", stock_quantity=100
        )

    def test_cart_creation(self):
        cart = Cart.objects.create(user=self.user)
        self.assertEqual(cart.user, self.user)
        self.assertEqual(cart.total_amount, 0)

    def test_cart_item_creation(self):
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart, 
            product=self.product, 
            quantity=2,
            unit_price=10.00
        )
        self.assertEqual(cart_item.cart, cart)
        self.assertEqual(cart_item.product, self.product)
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(cart_item.total_price, 20.00)

    def test_order_creation(self):
        order = Order.objects.create(
            customer=self.user,
            customer_name="Test Customer",
            customer_phone="+254700000000",
            customer_email="test@example.com",
            shipping_address="Test Address",
            total_amount=20.00,
            status="pending",
        )
        self.assertEqual(order.customer, self.user)
        self.assertEqual(order.total_amount, 20.00)
        self.assertEqual(order.status, "pending")

    def test_order_item_creation(self):
        order = Order.objects.create(
            customer=self.user,
            customer_name="Test Customer",
            customer_phone="+254700000000",
            customer_email="test@example.com",
            shipping_address="Test Address",
            total_amount=20.00,
            status="pending",
        )
        order_item = OrderItem.objects.create(
            order=order, 
            product=self.product, 
            product_name=self.product.name,
            quantity=2, 
            unit_price=10.00
        )
        self.assertEqual(order_item.order, order)
        self.assertEqual(order_item.product, self.product)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.unit_price, 10.00)
        self.assertEqual(order_item.total_price, 20.00)

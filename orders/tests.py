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


class OrderStockTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="buyer", email="buyer@example.com", password="testpass123"
        )
        self.category = Category.objects.create(name="Stock Category")
        self.product = Product.objects.create(
            name="Stocked Product", price=10.00, category=self.category, sku="STK001", stock_quantity=10
        )
        self.order = Order.objects.create(
            customer=self.user, customer_name="Buyer", customer_phone="+254700000000",
            customer_email="buyer@example.com", shipping_address="Somewhere", total_amount=30.00,
        )
        OrderItem.objects.create(
            order=self.order, product=self.product, product_name="Stocked Product",
            quantity=3, unit_price=10.00, total_price=30.00,
        )

    def test_confirming_order_deducts_stock_once(self):
        self.order.status = "confirmed"
        self.order.save()
        self.order.status = "processing"
        self.order.save()
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

    def test_confirming_uses_database_stock_not_stale_instance(self):
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=2)
        self.order.status = "confirmed"
        self.order.save()
        self.product.refresh_from_db()
        # Not enough stock: nothing deducted, no negative stock.
        self.assertEqual(self.product.stock_quantity, 2)


class OrderNumberTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="buyer2", email="buyer2@example.com", password="testpass123"
        )

    def _order(self):
        return Order.objects.create(
            customer=self.user, customer_name="B", customer_phone="1", customer_email="b@example.com",
            shipping_address="X", total_amount=1,
        )

    def test_order_number_follows_pk(self):
        o1, o2 = self._order(), self._order()
        self.assertEqual(o1.order_number, f"ORD{o1.pk:06d}")
        self.assertEqual(o2.order_number, f"ORD{o2.pk:06d}")


class CheckoutTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="shopper", email="shopper@example.com", password="testpass123"
        )
        self.category = Category.objects.create(name="Checkout Category")
        self.product = Product.objects.create(
            name="Cart Product", price=10.00, category=self.category, sku="CRT001", stock_quantity=10
        )
        self.client.force_login(self.user)
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2, unit_price=10.00)

    def test_checkout_creates_order_items_and_clears_cart(self):
        resp = self.client.post(reverse("orders:checkout"), {
            "customer_name": "Shopper", "customer_phone": "+254700000001",
            "customer_email": "shopper@example.com", "shipping_address": "Nairobi",
        })
        self.assertEqual(resp.status_code, 302)
        order = Order.objects.get(customer=self.user)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 2)
        self.assertFalse(Cart.objects.filter(user=self.user).exists())

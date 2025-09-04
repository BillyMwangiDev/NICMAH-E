from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Category, Product


class CatalogViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.category = Category.objects.create(name="Test Category", description="Test category description")
        self.product = Product.objects.create(
            name="Test Product",
            description="Test product description",
            price=10.00,
            stock_quantity=100,
            category=self.category,
            sku="TEST001",
        )

    def test_product_list_loads(self):
        resp = self.client.get(reverse("catalog:product_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("products", resp.context)
        self.assertEqual(len(resp.context["products"]), 1)

    def test_product_detail_loads(self):
        resp = self.client.get(reverse("catalog:product_detail", args=[self.product.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["product"], self.product)


class CatalogModelsTests(TestCase):
    def test_category_str(self):
        category = Category.objects.create(name="Test Category")
        self.assertEqual(str(category), "Test Category")

    def test_product_str(self):
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(name="Test Product", price=10.00, category=category, sku="TEST001")
        self.assertEqual(str(product), "Test Product")

    def test_product_stock_management(self):
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(
            name="Test Product", price=10.00, category=category, sku="TEST001", stock_quantity=100
        )

        self.assertEqual(product.stock_status, "In Stock")
        self.assertEqual(product.stock_quantity, 100)

        product.stock_quantity = 0
        self.assertEqual(product.stock_status, "Out of Stock")

        product.stock_quantity = 3
        self.assertEqual(product.stock_status, "Low Stock")

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


class VaccinesCategoryMigrationTests(TestCase):
    """The Vaccines category is seeded by data migration 0006."""

    EXPECTED_SUBCATEGORIES = {
        "Poultry": "vaccines-poultry",
        "Cattle": "vaccines-cattle",
        "Sheep & Goats": "vaccines-sheep-goats",
        "Pigs": "vaccines-pigs",
        "Dogs & Cats": "vaccines-dogs-cats",
    }

    def test_vaccines_category_exists_and_is_public(self):
        vaccines = Category.objects.get(slug="vaccines", parent=None)
        self.assertEqual(vaccines.name, "Vaccines")
        self.assertTrue(vaccines.is_active)
        self.assertFalse(vaccines.is_admin_only)

    def test_vaccines_has_animal_subcategories(self):
        vaccines = Category.objects.get(slug="vaccines", parent=None)
        subs = {c.name: c.slug for c in vaccines.get_all_subcategories()}
        self.assertEqual(subs, self.EXPECTED_SUBCATEGORIES)
        self.assertFalse(vaccines.subcategories.filter(is_admin_only=True).exists())

    def test_vaccines_appears_in_public_filter_dropdown(self):
        resp = self.client.get(reverse("catalog:product_list"))
        self.assertContains(resp, 'value="vaccines"')


class QueryCountTests(TestCase):
    """Listing and search views must not issue per-product queries."""

    def setUp(self):
        self.categories = [Category.objects.create(name=f"Cat {i}") for i in range(3)]
        for i in range(12):
            Product.objects.create(
                name=f"Product {i:02d}", description="A product description", price=10 + i,
                stock_quantity=5, category=self.categories[i % 3], sku=f"SKU{i:03d}",
            )

    def _count_queries(self, url):
        from django.core.cache import cache
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        cache.clear()  # measure cold-cache cost both times
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        return len(ctx.captured_queries)

    def test_product_list_query_count_does_not_grow_with_products(self):
        url = reverse("catalog:product_list")
        with_twelve = self._count_queries(url)
        Product.objects.exclude(name="Product 00").delete()
        with_one = self._count_queries(url)
        self.assertEqual(with_twelve, with_one)

    def test_search_suggestions_query_count_is_flat(self):
        url = reverse("catalog:search_suggestions") + "?q=Product"
        with_twelve = self._count_queries(url)
        Product.objects.exclude(name="Product 00").delete()
        self.assertEqual(with_twelve, self._count_queries(url))

    def test_api_product_search_query_count_is_flat(self):
        url = reverse("catalog:api_product_search") + "?q=Product"
        with_twelve = self._count_queries(url)
        Product.objects.exclude(name="Product 00").delete()
        self.assertEqual(with_twelve, self._count_queries(url))


class CategoryDetailTests(TestCase):
    def test_category_detail_is_paginated(self):
        category = Category.objects.create(name="Big Category")
        for i in range(30):
            Product.objects.create(
                name=f"Item {i:02d}", description="A product description", price=5,
                category=category, sku=f"BIG{i:03d}",
            )
        resp = self.client.get(reverse("catalog:category_detail", args=[category.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context["products"]), 24)
        self.assertTrue(resp.context["products"].has_next())


class CategoryCacheTests(TestCase):
    def test_new_category_appears_in_dropdown_immediately(self):
        url = reverse("catalog:product_list")
        self.client.get(url)  # warm the cache
        Category.objects.create(name="Brand New Category")
        resp = self.client.get(url)
        self.assertContains(resp, "Brand New Category")


class CategoryAdminTests(TestCase):
    def test_changelist_renders_product_counts_without_per_row_queries(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.client.force_login(admin_user)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        def query_count():
            with CaptureQueriesContext(connection) as ctx:
                resp = self.client.get(reverse("admin:catalog_category_changelist"))
            self.assertEqual(resp.status_code, 200)
            return len(ctx.captured_queries)

        Category.objects.create(name="Admin Cat 0")
        with_one = query_count()
        for i in range(1, 8):
            Category.objects.create(name=f"Admin Cat {i}")
        self.assertEqual(query_count(), with_one)


class ImageShrinkTests(TestCase):
    def _big_png(self, name="big.png", size=(3000, 2000)):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = BytesIO()
        Image.new("RGB", size, "green").save(buf, format="PNG")
        return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")

    def test_large_main_image_is_downsized_on_save(self):
        from PIL import Image
        category = Category.objects.create(name="Img Cat")
        product = Product.objects.create(
            name="Pictured", description="Has a picture", price=1, category=category,
            sku="IMG001", main_image=self._big_png(),
        )
        try:
            with Image.open(product.main_image.path) as img:
                self.assertLessEqual(max(img.size), 1200)
        finally:
            product.main_image.delete(save=False)

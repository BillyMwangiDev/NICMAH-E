import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product
from inventory.models import StockMovement
from .models import POSSale, POSSaleItem, POSSession


def make_cashier(username="cashier"):
    return get_user_model().objects.create_user(
        username=username, email=f"{username}@example.com", password="pass12345", role="admin"
    )


def make_product(name="Widget", sku="W1", stock=10, price="25.00"):
    category, _ = Category.objects.get_or_create(name="Test Category")
    return Product.objects.create(
        name=name, description="Ten chars or more", price=price, stock_quantity=stock,
        category=category, sku=sku,
    )


class POSSaleCreateTests(TestCase):
    def setUp(self):
        self.cashier = make_cashier()
        self.session = POSSession.objects.create(cashier=self.cashier)
        self.product = make_product()
        self.client.force_login(self.cashier)
        self.url = reverse("pos:sale_create")

    def post_sale(self, quantity=2):
        payload = {
            "items": [{"product_id": self.product.id, "quantity": quantity, "unit_price": "25.00"}],
            "payment_method": "cash",
            "amount_paid": "100.00",
        }
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_sale_completes_without_site_settings_row(self):
        # No SiteSettings row exists in the test DB; the view must not crash on it.
        resp = self.post_sale()
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertTrue(body["success"], body)
        self.assertEqual(body["print_status"], None)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)

    def test_insufficient_stock_is_rejected_and_nothing_saved(self):
        resp = self.post_sale(quantity=11)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(POSSale.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)


class StockDeductionTests(TestCase):
    def setUp(self):
        self.cashier = make_cashier()
        self.session = POSSession.objects.create(cashier=self.cashier)
        self.product = make_product(stock=5)
        self.sale = POSSale.objects.create(session=self.session, cashier=self.cashier, seller=self.cashier)

    def test_sale_item_deducts_stock_and_records_movement(self):
        POSSaleItem.objects.create(sale=self.sale, product=self.product, quantity=3, unit_price="25.00")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        movement = StockMovement.objects.get(product=self.product, reference_type="POSSale")
        self.assertEqual(movement.quantity, -3)
        self.assertEqual(movement.previous_stock, 5)
        self.assertEqual(movement.new_stock, 2)

    def test_sale_item_uses_database_value_not_stale_instance(self):
        # Simulate another cashier having sold 4 units after this instance was loaded.
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)
        with self.assertRaises(ValueError):
            POSSaleItem.objects.create(sale=self.sale, product=self.product, quantity=3, unit_price="25.00")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)


class SaleNumberTests(TestCase):
    def setUp(self):
        self.cashier = make_cashier()
        self.session = POSSession.objects.create(cashier=self.cashier)

    def test_sale_and_receipt_numbers_follow_pk(self):
        # A legacy row with a high number must not influence the next number.
        POSSale.objects.create(
            session=self.session, cashier=self.cashier, seller=self.cashier,
            sale_number="SALE-00050", receipt_number="RCP-00050",
        )
        s1 = POSSale.objects.create(session=self.session, cashier=self.cashier, seller=self.cashier)
        s2 = POSSale.objects.create(session=self.session, cashier=self.cashier, seller=self.cashier)
        self.assertEqual(s1.sale_number, f"SALE-{s1.pk:05d}")
        self.assertEqual(s1.receipt_number, f"RCP-{s1.pk:05d}")
        self.assertEqual(s2.sale_number, f"SALE-{s2.pk:05d}")
        self.assertNotEqual(s1.sale_number, s2.sale_number)
        s1.refresh_from_db()
        self.assertEqual(s1.sale_number, f"SALE-{s1.pk:05d}")

    def test_explicit_sale_number_is_kept(self):
        s = POSSale.objects.create(
            session=self.session, cashier=self.cashier, seller=self.cashier, sale_number="LEGACY-1"
        )
        s.refresh_from_db()
        self.assertEqual(s.sale_number, "LEGACY-1")


class ProductSearchTests(TestCase):
    def setUp(self):
        self.cashier = make_cashier("searcher")
        self.client.force_login(self.cashier)
        self.url = reverse("pos:product_search")
        from .models import Barcode
        self.exact = make_product(name="Aspirin", sku="ASP1", stock=20)
        self.starts = make_product(name="Aspirin Forte", sku="ASP2", stock=20)
        self.contains = make_product(name="Baby Aspirin Syrup", sku="BAS1", stock=20)
        self.by_code = make_product(name="Unrelated Tonic", sku="UT1", stock=20)
        Barcode.objects.create(barcode="123456", product=self.by_code)
        Barcode.objects.create(barcode="OLD999", product=self.by_code, is_active=False)

    def names(self, q, **extra):
        params = {"q": q, **extra}
        resp = self.client.get(self.url, params)
        self.assertEqual(resp.status_code, 200)
        return [p["name"] for p in resp.json()["products"]]

    def test_exact_name_ranks_before_prefix_before_contains(self):
        self.assertEqual(self.names("Aspirin"), ["Aspirin", "Aspirin Forte", "Baby Aspirin Syrup"])

    def test_barcode_match_is_found(self):
        self.assertEqual(self.names("123456"), ["Unrelated Tonic"])

    def test_limit_is_clamped_and_bad_values_ignored(self):
        self.assertEqual(len(self.names("Aspirin", limit=1)), 1)
        self.assertEqual(len(self.names("Aspirin", limit="abc")), 3)
        self.assertEqual(len(self.names("Aspirin", limit=100000)), 3)

    def test_barcodes_returned_without_per_product_queries(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(self.url, {"q": "Tonic"})
        body = resp.json()["products"]
        self.assertEqual(body[0]["barcodes"], ["123456"])
        for i in range(10):
            make_product(name=f"Tonic {i}", sku=f"TON{i}", stock=3)
        with CaptureQueriesContext(connection) as ctx2:
            self.client.get(self.url, {"q": "Tonic"})
        self.assertEqual(len(ctx.captured_queries), len(ctx2.captured_queries))

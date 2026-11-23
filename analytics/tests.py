from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Count, Sum
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from catalog.models import Category, Product
from .models import Sales, SalesItem
from .views import daily_series


def make_sale(when, amount="10.00", n=1):
    return Sales.objects.create(
        sale_number=f"S-{when.timestamp()}-{n}", sale_type="pos", status="completed",
        customer_name="Walk-in", subtotal=Decimal(amount), total_amount=Decimal(amount), amount_paid=Decimal(amount),
        payment_method="cash", created_at=when,
    )


class DailySeriesTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        # created_at is auto_now_add; override after create.
        for days_ago, amount in [(0, "10.00"), (0, "5.00"), (2, "7.50"), (9, "99.00")]:
            sale = make_sale(self.now, amount, n=f"{days_ago}-{amount}")
            Sales.objects.filter(pk=sale.pk).update(created_at=self.now - timedelta(days=days_ago))

    def test_series_fills_missing_days_and_sums_in_one_query(self):
        with CaptureQueriesContext(connection) as ctx:
            series = daily_series(
                Sales.objects.filter(status="completed"), "created_at", self.now, days=7,
                aggregate=Sum("total_amount"),
            )
        self.assertEqual(len(ctx.captured_queries), 1)
        self.assertEqual(len(series), 7)
        self.assertEqual(series[-1], 15.0)   # today: 10 + 5
        self.assertEqual(series[-3], 7.5)    # two days ago
        self.assertEqual(series[0], 0)       # six days ago, nothing
        self.assertEqual(sum(series), 22.5)  # the 9-day-old sale is outside the window

    def test_series_counts_rows_by_default(self):
        series = daily_series(Sales.objects.all(), "created_at", self.now, days=7)
        self.assertEqual(series[-1], 2)


class DashboardTests(TestCase):
    def test_dashboard_renders_for_admin(self):
        admin = get_user_model().objects.create_user(
            username="an", email="an@example.com", password="pass12345", role="admin", is_staff=True
        )
        self.client.force_login(admin)
        resp = self.client.get(reverse("analytics:dashboard"))
        self.assertEqual(resp.status_code, 200)

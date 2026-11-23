from django.test import TestCase
from django.urls import reverse


class CoreViewsTests(TestCase):
    def test_home_page_loads(self):
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("site_name", resp.context)



class HealthCheckTests(TestCase):
    def test_health_ok_reports_db_cache_and_live_timestamp(self):
        resp = self.client.get(reverse("core:health_check"))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["database"], "healthy")
        self.assertEqual(body["cache"], "healthy")
        self.assertNotEqual(body["timestamp"], "2025-09-04T12:00:00Z")
        self.assertTrue(body["timestamp"].startswith("20"))


class SiteSettingsCacheTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        from django.contrib.sites.models import Site
        from core.models import SiteSettings
        self.site = Site.objects.get_current()
        self.settings = SiteSettings.objects.create(site=self.site, site_name="Cached Name")

    def test_second_request_does_not_query_site_settings(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        self.client.get(reverse("core:home"))
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("core:home"))
        site_settings_queries = [q["sql"] for q in ctx.captured_queries if "core_sitesettings" in q["sql"]]
        # home() itself reads SiteSettings once; the context processor must add none.
        self.assertLessEqual(len(site_settings_queries), 1, site_settings_queries)

    def test_save_invalidates_cache(self):
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.context["site_name"], "Cached Name")
        self.settings.site_name = "New Name"
        self.settings.save()
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.context["site_name"], "New Name")


class AsyncMailTests(TestCase):
    def test_send_mail_async_delivers_via_backend(self):
        from django.core import mail
        from core.mail import send_mail_async
        thread = send_mail_async(
            subject="Stock alert", message="Low stock", from_email="a@example.com",
            recipient_list=["b@example.com"],
        )
        thread.join(timeout=5)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Stock alert")

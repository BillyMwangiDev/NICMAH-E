from django.test import TestCase
from django.urls import reverse


class CoreViewsTests(TestCase):
    def test_home_page_loads(self):
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("site_name", resp.context)


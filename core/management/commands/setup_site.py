"""
Management command to set up default site settings for NICMAH.
"""

from django.core.management.base import BaseCommand
from core.models import SiteSettings
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = "Set up default site settings for NICMAH"

    def handle(self, *args, **options):
        try:
            # Check if settings already exist
            if SiteSettings.objects.exists():
                self.stdout.write(self.style.WARNING("Site settings already exist. Skipping setup."))
                return

            # Get or create default site
            site, created = Site.objects.get_or_create(
                id=1,
                defaults={'domain': 'nicmahagrovet.com', 'name': 'NICMAH'}
            )

            # Create default site settings
            settings = SiteSettings.objects.create(
                site=site,
                site_name="NICMAH",
                tagline=(
                    "Farmers focused business specializing in livestock farming "
                    "and crop farming for over two decades."
                ),
                business_description=(
                    "NICMAH is a farmers focused business that majors on livestock farming "
                    "and crop farming for over two decades."
                ),
                mission_statement=(
                    "Our mission is to ensure quality, hardy and resistant herds are maintained "
                    "and passed on through generations."
                ),
                vision_statement=(
                    "Our goal is to help farmers achieve their goals and educating " "them to ensure their prosperity."
                ),
                livestock_services=(
                    "• AI (Artificial Insemination) services\n• Best livestock breeding practices\n"
                    "• Quality semen and breeding materials"
                ),
                crop_services=(
                    "• Quality seeds\n• Foliar applications\n• Pest control products\n"
                    "• Crop management solutions\n• Market access support"
                ),
                contact_email="nicmahagrovet@gmail.com",
                phone_number="0726476128/0740368581",
                address="Naromoru town, Timberland building near KFA",
                facebook_url="https://facebook.com/NicmahAgrovet",
                tiktok_url="https://tiktok.com/@Nicmah",
                instagram_url="",
                twitter_url="",
                currency="KES",
                tax_rate=0.00,
                business_hours="Monday - Friday: 8:00 AM - 6:00 PM\nSaturday: 8:00 AM - 4:00 PM\nSunday: Closed",
                years_in_business=20,
                cattle_ai_count=1000,
                farmers_served=1000,
            )

            self.stdout.write(self.style.SUCCESS(f"Successfully created site settings for {settings.site_name}"))

            # Display the created settings
            self.stdout.write("\nSite Settings Summary:")
            self.stdout.write(f"  Site Name: {settings.site_name}")
            self.stdout.write(f"  Contact Email: {settings.contact_email}")
            self.stdout.write(f"  Phone: {settings.phone_number}")
            self.stdout.write(f"  Address: {settings.address}")
            self.stdout.write(f"  Currency: {settings.currency}")
            self.stdout.write(f"  Years in Business: {settings.years_in_business}")
            self.stdout.write(f"  Cattle AI Count: {settings.cattle_ai_count}")
            self.stdout.write(f"  Farmers Served: {settings.farmers_served}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating site settings: {str(e)}"))

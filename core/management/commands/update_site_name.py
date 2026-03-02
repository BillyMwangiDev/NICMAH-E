"""
Management command to update site name to NICMAH
"""
from django.core.management.base import BaseCommand
from core.models import SiteSettings


class Command(BaseCommand):
    help = "Update site name to NICMAH in all SiteSettings records"

    def handle(self, *args, **options):
        # Update all SiteSettings records
        updated = SiteSettings.objects.update(site_name="NICMAH")
        
        # Also update business_description if it contains "Nicmah Agrovet"
        settings = SiteSettings.objects.all()
        for setting in settings:
            if "Nicmah Agrovet" in setting.business_description:
                setting.business_description = setting.business_description.replace(
                    "Nicmah Agrovet", "NICMAH"
                )
                setting.save()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated} SiteSettings record(s) to use "NICMAH" as site name.'
            )
        )

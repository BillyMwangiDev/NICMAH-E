"""
Management command to create the Bull Semen category.
"""
from django.core.management.base import BaseCommand
from catalog.models import Category


class Command(BaseCommand):
    help = "Create Bull Semen category with admin-only access"

    def handle(self, *args, **options):
        """Create or update Bull Semen category."""
        category, created = Category.objects.get_or_create(
            name="Bull Semen",
            defaults={
                "slug": "bull-semen",
                "description": "Premium bull semen products for artificial insemination. Available only to authorized admin users.",
                "is_active": True,
                "is_admin_only": True,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Successfully created category: {category.name}"
                )
            )
            self.stdout.write(f"  Slug: {category.slug}")
            self.stdout.write(f"  Admin Only: {category.is_admin_only}")
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"Category '{category.name}' already exists."
                )
            )
            # Update existing category to be admin-only
            category.is_admin_only = True
            category.save()
            self.stdout.write(
                self.style.SUCCESS("✓ Updated category to be admin-only")
            )


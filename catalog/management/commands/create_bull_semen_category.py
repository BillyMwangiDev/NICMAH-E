"""
Management command to create the Bull Semen category with subcategories for different cow breeds.
"""
from django.core.management.base import BaseCommand
from catalog.models import Category


class Command(BaseCommand):
    help = "Create Bull Semen category with subcategories for different cow breeds"

    # Common dairy and beef cow breeds sold in Kenya/East Africa
    COW_BREEDS = [
        {
            "name": "Friesian",
            "description": "High-yield dairy breed known for excellent milk production. Ideal for dairy farming operations.",
        },
        {
            "name": "Ayrshire",
            "description": "Hardy dairy breed with good milk production and excellent adaptability to various climates.",
        },
        {
            "name": "Jersey",
            "description": "Small dairy breed with high butterfat content in milk. Efficient and easy to manage.",
        },
        {
            "name": "Guernsey",
            "description": "Dairy breed known for golden-colored milk with high butterfat content.",
        },
        {
            "name": "Holstein",
            "description": "World's highest-producing dairy breed. Excellent for commercial dairy operations.",
        },
        {
            "name": "Boran",
            "description": "Indigenous beef breed known for heat tolerance, disease resistance, and hardiness.",
        },
        {
            "name": "Sahiwal",
            "description": "Dual-purpose breed (milk and beef) known for tick resistance and heat tolerance.",
        },
        {
            "name": "Brahman",
            "description": "Hardy beef breed known for adaptability, heat tolerance, and disease resistance.",
        },
        {
            "name": "Charolais",
            "description": "Large beef breed known for rapid growth and high-quality meat production.",
        },
        {
            "name": "Hereford",
            "description": "Popular beef breed known for docility, hardiness, and good meat quality.",
        },
        {
            "name": "Angus",
            "description": "Premium beef breed known for marbling, meat quality, and ease of calving.",
        },
        {
            "name": "Simmental",
            "description": "Dual-purpose breed known for large size, good milk production, and quality beef.",
        },
        {
            "name": "Other Breeds",
            "description": "Other specialized cow breeds and crossbreeds available for artificial insemination.",
        },
    ]

    def handle(self, *args, **options):
        """Create or update Bull Semen category and its subcategories."""
        # Create or get the main Bull Semen category
        category, created = Category.objects.get_or_create(
            name="Bull Semen",
            parent=None,
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
                    f"Successfully created category: {category.name}"
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
                self.style.SUCCESS("Updated category to be admin-only")
            )

        # Create subcategories for each cow breed
        self.stdout.write("\nCreating subcategories for cow breeds...")
        created_count = 0
        updated_count = 0

        for breed in self.COW_BREEDS:
            subcategory, sub_created = Category.objects.get_or_create(
                name=breed["name"],
                parent=category,
                defaults={
                    "description": breed["description"],
                    "is_active": True,
                    "is_admin_only": True,  # Inherit admin-only from parent
                }
            )

            if sub_created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [OK] Created subcategory: {subcategory.name}"
                    )
                )
            else:
                updated_count += 1
                # Update existing subcategory to ensure it's admin-only
                subcategory.is_admin_only = True
                subcategory.description = breed["description"]
                subcategory.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"  [UPDATE] Updated subcategory: {subcategory.name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {created_count} new subcategories created, {updated_count} subcategories updated."
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Total subcategories under 'Bull Semen': {category.get_all_subcategories().count()}"
            )
        )

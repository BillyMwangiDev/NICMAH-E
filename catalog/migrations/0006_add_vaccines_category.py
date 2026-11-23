"""
Data migration: seed the public "Vaccines" category with animal-type subcategories.

Idempotent (get_or_create). Slugs are set explicitly because the model's custom
save() is not available on historical models inside migrations.
"""

from django.db import migrations


PARENT = {
    "name": "Vaccines",
    "slug": "vaccines",
    "description": "Livestock and pet vaccines for disease prevention. Keep refrigerated as directed.",
}

SUBCATEGORIES = [
    ("Poultry", "vaccines-poultry", "Vaccines for chickens and other poultry (Newcastle, Gumboro, fowl pox, fowl typhoid)."),
    ("Cattle", "vaccines-cattle", "Vaccines for dairy and beef cattle (FMD, anthrax, blackquarter, lumpy skin disease, ECF)."),
    ("Sheep & Goats", "vaccines-sheep-goats", "Vaccines for sheep and goats (PPR, CCPP, enterotoxaemia, sheep and goat pox)."),
    ("Pigs", "vaccines-pigs", "Vaccines for pigs (swine fever, erysipelas, and related diseases)."),
    ("Dogs & Cats", "vaccines-dogs-cats", "Vaccines for dogs and cats (rabies, parvovirus, distemper, feline core vaccines)."),
]


def create_vaccines_category(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")

    parent, _ = Category.objects.get_or_create(
        name=PARENT["name"],
        parent=None,
        defaults={
            "slug": PARENT["slug"],
            "description": PARENT["description"],
            "is_active": True,
            "is_admin_only": False,
        },
    )

    for name, slug, description in SUBCATEGORIES:
        Category.objects.get_or_create(
            name=name,
            parent=parent,
            defaults={
                "slug": slug,
                "description": description,
                "is_active": True,
                "is_admin_only": False,
            },
        )


def remove_vaccines_category(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    parent = Category.objects.filter(name=PARENT["name"], parent=None).first()
    if parent is None:
        return
    # Only remove seeded rows that hold no products; never delete user data.
    for sub in parent.subcategories.all():
        if not sub.products.exists():
            sub.delete()
    if not parent.products.exists() and not parent.subcategories.exists():
        parent.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_alter_product_additional_images"),
    ]

    operations = [
        migrations.RunPython(create_vaccines_category, remove_vaccines_category),
    ]

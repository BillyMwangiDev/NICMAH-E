"""
Seed the public "Vaccines" category with animal-type subcategories.
Idempotent (get_or_create on slug). Category.name is globally unique in this model,
so subcategory names carry the word "Vaccines" to avoid clashing with existing
categories such as "Poultry Products".
"""

from django.db import migrations

PARENT = ("Vaccines", "vaccines", "Livestock and pet vaccines for disease prevention. Keep refrigerated as directed.")

SUBCATEGORIES = [
    ("Poultry Vaccines", "vaccines-poultry", "Newcastle, Gumboro, fowl pox, fowl typhoid and other poultry vaccines."),
    ("Cattle Vaccines", "vaccines-cattle", "FMD, anthrax, blackquarter, lumpy skin disease, ECF and other cattle vaccines."),
    ("Sheep & Goat Vaccines", "vaccines-sheep-goats", "PPR, CCPP, enterotoxaemia, sheep and goat pox vaccines."),
    ("Pig Vaccines", "vaccines-pigs", "Swine fever, erysipelas and related pig vaccines."),
    ("Pet Vaccines", "vaccines-dogs-cats", "Rabies, parvovirus, distemper and feline core vaccines for dogs and cats."),
]


def create_vaccines(apps, schema_editor):
    Category = apps.get_model("inventory", "Category")
    parent, _ = Category.objects.get_or_create(
        slug=PARENT[1],
        defaults={"name": PARENT[0], "description": PARENT[2], "is_active": True, "is_admin_only": False},
    )
    for name, slug, description in SUBCATEGORIES:
        Category.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "description": description, "parent": parent,
                      "is_active": True, "is_admin_only": False},
        )


def remove_vaccines(apps, schema_editor):
    Category = apps.get_model("inventory", "Category")
    for _, slug, _ in SUBCATEGORIES:
        cat = Category.objects.filter(slug=slug).first()
        if cat is not None and not cat.products.exists():
            cat.delete()
    parent = Category.objects.filter(slug=PARENT[1]).first()
    if parent is not None and not parent.products.exists() and not parent.subcategories.exists():
        parent.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0004_purchaseorder_supplier_stocklog_reference_and_more"),
    ]

    operations = [
        migrations.RunPython(create_vaccines, remove_vaccines),
    ]

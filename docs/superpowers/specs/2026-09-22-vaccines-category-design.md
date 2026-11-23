# Vaccines category — design

Date: 2026-09-22

## Goal

Add a public, top-level "Vaccines" product category with animal-type subcategories, and make sure it reaches the cPanel production database through the normal deploy path.

## Findings

Categories are rows in `catalog.Category`. Every consumer (product list filter dropdown, category detail page, POS product search and cards, analytics category pie chart, Django admin) reads from that table. Nothing hardcodes the category list. Adding a category is therefore a data change with a repeatable delivery mechanism.

## Decision

Django data migration `catalog/migrations/0006_add_vaccines_category.py`.

- Creates top-level category **Vaccines** (slug `vaccines`, `is_active=True`, `is_admin_only=False`).
- Creates five subcategories with parent = Vaccines: **Poultry**, **Cattle**, **Sheep & Goats**, **Pigs**, **Dogs & Cats**. Slugs follow the model's convention `vaccines-<slug>`, set explicitly because the model's custom `save()` is not available inside migrations.
- Uses `get_or_create` keyed on `(name, parent)` so re-running is a no-op.
- Reverse migration deletes these categories only when they hold no products.

Rejected: a management command (must be remembered on every deploy) and manual creation in admin (no record in repo, local and prod drift).

## Code and template changes

None required. Verified by grep: no template or view enumerates category names.

## Testing

`catalog/tests.py` gains `VaccinesCategoryMigrationTests` asserting after migrations: Vaccines exists, is public and active, has exactly five active subcategories with the expected names and slugs.

## Deploy to cPanel

1. Pull the code into the app directory.
2. In cPanel Terminal, with the app's virtualenv active: `python manage.py migrate catalog`.
3. Restart the Passenger app (`touch tmp/restart.txt` or Restart in Setup Python App).

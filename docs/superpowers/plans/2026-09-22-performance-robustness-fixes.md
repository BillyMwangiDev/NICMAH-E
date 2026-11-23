# Performance and Robustness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 25 findings in `docs/PERFORMANCE_AND_ROBUSTNESS_BRAINSTORM.md` so the site serves pages with `DEBUG=False` on cPanel, cannot oversell stock, and loads faster.

**Architecture:** Settings become env-driven with safe defaults (file cache, WhiteNoise, SMTP from env). Stock deduction moves behind row locks and `F()` updates inside transactions. Sequence numbers derive from primary keys. Views gain `select_related` / `prefetch_related`, pagination, and single-query aggregates. Tailwind is compiled once into a static file and the runtime CDN script is removed.

**Tech Stack:** Django 5.2, WhiteNoise, Pillow, Tailwind CLI v3 (build-time only, Node not needed on the server).

**Status:** all tasks implemented 2026-09-22; 43 tests pass. Deviations: Chart.js scripts were left without `defer` because most dashboards call `new Chart` inline before `DOMContentLoaded`; `main.js` stays at the end of `<body>` without `defer` for the same reason.

**Working rules:** Run `.venv_preview/bin/python manage.py test` after every task. Nothing is committed unless Billy asks. Each task lists its verification.

---

## Batch A: production-breaking settings (items 1, 7, 8, 9, 11, 23)

### Task A1: Cache backend that works on cPanel (item 1)
- Modify: `nichmah_agrovet/settings.py` CACHES block.
- Non-DEBUG default becomes `django.core.cache.backends.filebased.FileBasedCache` at `BASE_DIR / "cache"`, overridable with `CACHE_BACKEND` / `CACHE_LOCATION` env vars so Redis can still be used where it exists. Add `cache/` to `.gitignore`.
- Verify: `DEBUG=False SECRET_KEY=x ALLOWED_HOSTS=testserver .venv_preview/bin/python manage.py check` passes and `python -c "from django.core.cache import cache; cache.set('a',1); assert cache.get('a')==1"` under the same env.

### Task A2: Safe defaults for DEBUG and SECRET_KEY (item 7)
- Modify: `settings.py` lines 23-28.
- `DEBUG` defaults to `False`. `SECRET_KEY` has no default: when unset and `DEBUG` is False raise `ImproperlyConfigured`; when `DEBUG` is True fall back to a dev key so local runs still work.
- Test: `core/tests.py` gets no test here (settings import-time). Verify: `DEBUG=False .venv_preview/bin/python manage.py check` without SECRET_KEY fails with the message; with `SECRET_KEY=x` it passes.
- Local dev impact: `.venv_preview` runs need `DEBUG=True` in `.env`. Create `.env.example` documenting every variable.

### Task A3: Guard SiteSettings in POS sale creation (item 8)
- Modify: `pos/views.py:104,219`. Rename local `settings` to `site_settings`; guard with `if site_settings and site_settings.printer_enabled and site_settings.auto_print_receipts`.
- Test: `pos/tests.py::POSSaleCreateTests::test_sale_completes_without_site_settings_row` posts a sale with no `SiteSettings` row and asserts 200 and `success: True`.

### Task A4: Email configuration and non-blocking stock alerts (item 9)
- Modify: `settings.py` add `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `EMAIL_TIMEOUT=10` from env. Default backend: console in DEBUG, SMTP otherwise.
- Create: `core/mail.py` with `send_mail_async(**kwargs)` that runs `django.core.mail.send_mail` in a daemon thread and logs failures.
- Modify: `inventory/notifications.py` two `send_mail(` calls use `send_mail_async`. Document email in `inventory/document_generation.py` stays synchronous (the user clicks "send" and expects a result) but now benefits from `EMAIL_TIMEOUT`.
- Test: `core/tests.py::AsyncMailTests` uses `locmem` backend and asserts one message lands in `mail.outbox` after the thread joins.

### Task A5: WhiteNoise and hashed, compressed static files (item 11)
- Modify: `requirements.txt` add `whitenoise==6.9.0`. `settings.py`: insert `whitenoise.middleware.WhiteNoiseMiddleware` right after `SecurityMiddleware`; add `STORAGES` with `CompressedManifestStaticFilesStorage` for staticfiles (only when not DEBUG, so tests and dev do not need `collectstatic`). Add `staticfiles/` to `.gitignore` if missing.
- Verify: `DEBUG=False SECRET_KEY=x .venv_preview/bin/python manage.py collectstatic --noinput` produces `staticfiles/staticfiles.json` and `.gz` files.

### Task A6: Rotating log files (item 23)
- Modify: `settings.py` LOGGING handlers `file` and `security_file` -> `logging.handlers.RotatingFileHandler`, `maxBytes=5*1024*1024`, `backupCount=5`.
- Verify: `manage.py check` passes, log file still written on a request in tests.

## Batch B: stock and money correctness (items 2, 3, 5, 6)

### Task B1: Row-locked stock deduction in POS (item 2)
- Modify: `pos/models.py` `POSSaleItem.save()`: when new, `Product.objects.select_for_update().get(pk=self.product_id)` inside `transaction.atomic()`, check stock on the locked row, `Product.objects.filter(pk=..).update(stock_quantity=F("stock_quantity") - qty)`, then `refresh_from_db(fields=["stock_quantity"])` before recording the `StockMovement`.
- Modify: `pos/views.py:135` product lookup uses `select_for_update()` so the stock check at line 154 reads a locked row.
- Test: `pos/tests.py::StockDeductionTests::test_sale_item_deducts_stock_and_records_movement`, `test_sale_item_rejects_insufficient_stock`.

### Task B2: Row-locked stock deduction in orders and transactional checkout (items 2, 5)
- Modify: `orders/models.py` `Order.save()`: wrap in `transaction.atomic()`; lock each `order_item.product` with `select_for_update()`, `F()` update.
- Modify: `orders/views.py` checkout POST branch wrapped in `transaction.atomic()`.
- Test: `orders/tests.py::OrderStockTests::test_confirming_order_deducts_stock_once` (save twice with status confirmed, stock deducted once) and `OrdersViewsTests::test_checkout_creates_order_items_and_clears_cart`.

### Task B3: Print receipt after commit (item 3)
- Modify: `pos/views.py`: move the auto-print block out of `with transaction.atomic():` so it runs after commit; use `transaction.on_commit` is unnecessary since the block sits after the `with`.
- Test: `pos/tests.py::POSSaleCreateTests::test_sale_response_shape` still passes; verify by reading the diff that `printer.print_receipt` is outside the `with`.

### Task B4: Collision-free sale, receipt, and order numbers (item 6)
- Modify: `pos/models.py` `POSSale.save()`: on insert, save with a temporary unique placeholder (`uuid4` hex) for `sale_number` / `receipt_number` when unset, then set `SALE-{pk:05d}` / `RCP-{pk:05d}` and `update()` those two columns. Delete the `Max()` scanning blocks.
- Modify: `orders/models.py` `Order.save()`: same with `ORD{pk:06d}`.
- Note: local and prod have zero sales and zero orders (verified locally; prod confirmed by Billy at deploy time), so no legacy collisions.
- Test: `pos/tests.py::SaleNumberTests::test_sale_numbers_follow_pk`, `orders/tests.py::OrderNumberTests::test_order_number_follows_pk`.

## Batch C: query hygiene (items 12, 13, 14, 15, 17, 19, 20, 21, 24)

### Task C1: Product list joins and image `{% with %}` (item 12)
- Modify: `catalog/views.py` `product_list` base queryset `.select_related("category").prefetch_related(Prefetch("images", queryset=ProductImage.objects.filter(is_active=True).order_by("order")))`; `total_products` uses `paginator.count`.
- Modify: `catalog/templates/catalog/product_list.html:140-143` `{% with first_image=product.images.all|first %}`.
- Test: `catalog/tests.py::QueryCountTests::test_product_list_query_count_is_flat` with 12 products across 3 categories asserts `assertNumQueries` upper bound (measure once, assert `<=` measured, and that it equals the count with 1 product + constant).

### Task C2: POS product search prefetch, SQL ranking, clamped limit (item 13)
- Modify: `pos/views.py` `pos_product_search`: `Prefetch("barcodes", queryset=Barcode.objects.filter(is_active=True), to_attr="active_barcodes")`; ranking via `annotate(relevance=Case(When(...), ...))` and `order_by("-relevance", "-stock_quantity", "name")`; `limit = min(max(int(...), 1), 50)` with `ValueError` -> 10.
- Test: `pos/tests.py::ProductSearchTests::test_exact_name_ranks_first`, `test_limit_is_clamped`, `test_barcodes_returned_without_extra_queries` (`assertNumQueries`).

### Task C3: `select_related` on search endpoints (item 14)
- Modify: `catalog/views.py` `search_suggestions`, `api_product_search`, `quick_search` add `.select_related("category")`; `quick_search` `total_results = len(products)`.
- Test: `catalog/tests.py::QueryCountTests::test_search_suggestions_query_count`.

### Task C4: Analytics 7-day trends in one query per metric (item 15)
- Modify: `analytics/views.py:95-189`: a helper `_daily_series(qs, date_field, agg, start, end)` using `TruncDate` + `values().annotate()`, then fill missing days with 0. Replaces four loops.
- Test: `analytics/tests.py::DailySeriesTests::test_series_fills_missing_days_and_sums`.

### Task C5: Cached SiteSettings in the context processor (item 17)
- Modify: `core/context_processors.py` wrap the dict build in `cache.get_or_set("site_settings_ctx", builder, 300)`; `core/models.py` `SiteSettings.save()` and a `post_delete` receiver clear the key.
- Test: `core/tests.py::SiteSettingsCacheTests::test_context_processor_hits_db_once_across_requests`, `test_save_invalidates_cache`.

### Task C6: Bound the unbounded querysets (items 19, 20)
- Modify: `pos/views.py:281` drop `products` from the GET context (template only uses the AJAX endpoint; verified `grep` shows no `{% for product in products %}` in `sale_create.html`).
- Modify: `inventory/views.py:341` replace `Product.objects.all()` with `Product.objects.count()` as `product_count` and update `stock_movements.html:336,388` (check what line 388 iterates; if a select of products for a filter, keep it but `.only("id","name").order_by("name")`).
- Modify: `catalog/views.py` `category_detail` paginate 24 with `select_related("category")`; `product_detail` related products `.select_related("category")`.
- Test: `catalog/tests.py::CategoryDetailTests::test_category_detail_is_paginated`.

### Task C7: Indexes on hot columns (item 21)
- Modify: `analytics/models.py` `Sales.Meta`, `orders/models.py` `Order.Meta`, `pos/models.py` `POSSale.Meta`: `indexes = [Index(fields=["created_at"]), Index(fields=["status", "created_at"])]`.
- Run `makemigrations analytics orders pos`. Verify migration files exist and `migrate` applies.

### Task C8: Category admin count annotation (item 24)
- Modify: `catalog/admin.py` `CategoryAdmin.get_queryset` annotates `_product_count=Count("products")`; `product_count` reads `obj._product_count`.
- Verify: admin changelist renders in test `catalog/tests.py::CategoryAdminTests::test_changelist_renders`.

## Batch D: front-end speed (items 10, 16, 18, 20)

### Task D1: Build Tailwind once (item 10)
- Create: `tailwind.config.js` (content: all `*/templates/**/*.html`, `core/static/js/*.js`; theme extend copied from `base.html` inline config), `core/static/css/tailwind.src.css` (`@tailwind base; components; utilities`), `package.json` with a `build:css` script.
- Run: `npx tailwindcss@3 -c tailwind.config.js -i core/static/css/tailwind.src.css -o core/static/css/tailwind.css --minify`.
- Modify: `core/templates/base.html`: remove the CDN script and the inline `tailwind.config` block; add `<link rel="stylesheet" href="{% static 'css/tailwind.css' %}">`; add `<link rel="preconnect">` for `cdnjs.cloudflare.com`, `fonts.googleapis.com`, `fonts.gstatic.com`; `defer` on `main.js`.
- Also: every template that loads Chart.js gets `defer`... only where the inline script that uses `Chart` is itself deferred or wrapped in `DOMContentLoaded`; otherwise leave (verify each).
- Verify: built CSS exists and is under 200 KB; grep for dynamic class construction (`class="${`, `` `bg-${ ``) in templates and JS; add a `safelist` for any found. Product list renders with Tailwind classes present in the built CSS (spot-check `grid-cols-4`, `bg-agro-green`).

### Task D2: Lazy images and upload-time thumbnails (item 16)
- Modify: `<img>` tags in `product_list.html`, `home.html`, `quick_search.html`, `product_detail.html` (related products), `educational/_article_cards.html`, `article_list.html`: add `loading="lazy" decoding="async"`. Skip PDF templates and the logo in `base.html`.
- Modify: `catalog/models.py`: `Product.save()` and `ProductImage.save()` call a shared `core/images.py::shrink_image(field, max_side=1200, quality=82)` that downsizes in place with Pillow when the file is larger.
- Test: `catalog/tests.py::ImageShrinkTests::test_large_upload_is_downsized` builds a 3000x2000 PNG in memory, saves a Product, asserts width <= 1200.

### Task D3: Fragment cache for the category dropdown (item 18)
- Modify: `catalog/views.py` category dropdown list via `cache.get_or_set(f"catalog_categories:{is_admin}", ..., 300)`; `catalog/models.py` `Category.save()`/`delete()` clear both keys. Product grid is left uncached on purpose: cards show live stock and the page is already paginated and joined (C1).
- Test: `catalog/tests.py::CategoryCacheTests::test_new_category_appears_immediately`.

## Batch E: operability (items 4, 22, 25)

### Task E1: Health check (item 22)
- Modify: `core/views.py` `health_check`: `SELECT 1` via cursor, cache round-trip, `timezone.now().isoformat()`, catch `Exception`.
- Test: `core/tests.py::HealthCheckTests::test_health_ok`.

### Task E2: MySQL readiness (item 4)
- Modify: `requirements.txt` add `mysqlclient==2.2.7`. `.env.example` documents `DB_ENGINE=django.db.backends.mysql` and the connection vars, plus `OPTIONS` charset. `settings.py` DATABASES adds `"OPTIONS": {"charset": "utf8mb4"}` only when the engine is MySQL, `CONN_MAX_AGE=60`.
- Not done here: creating the database in cPanel and migrating data. Instructions go in the final report.

### Task E3: Tests (item 25)
- Covered by tests in every task above. Final: `.venv_preview/bin/python manage.py test` all green.

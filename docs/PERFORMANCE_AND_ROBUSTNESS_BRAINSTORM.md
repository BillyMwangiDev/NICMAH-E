# NICMAH-E: making the site faster and the backend sturdier

Date: 2026-09-22. Every item below was verified against the current source.

**Status (2026-09-22): all 25 items implemented** in the working tree, covered by 43 passing tests. See `docs/superpowers/plans/2026-09-22-performance-robustness-fixes.md` for the task list and the deploy notes below. Item 4 (MySQL) is code-ready; creating the database in cPanel and moving the data is a manual step.

Context: production runs on shared cPanel (Passenger), defaults to SQLite, loads Tailwind from a CDN at runtime, has 15 tests covering ~4,500 lines of view code, and has no background worker.

## Tier 1: things that will break or corrupt data under real load

| # | Problem | Where | Fix | Effort |
|---|---------|-------|-----|--------|
| 1 | Production cache points at Redis, but Redis is not installed and `django-redis` is not in requirements. With `DEBUG=False` the security middleware touches the cache on every request, so the site cannot serve a page. | `nichmah_agrovet/settings.py:240-249`, `security_middleware.py:162,174` | Use `DatabaseCache` or `FileBasedCache` on cPanel. One settings change plus `createcachetable`. | Small |
| 2 | Stock deduction is read-modify-write with no row lock. Two cashiers selling the last unit both succeed. Same bug in web-shop orders. | `pos/models.py:720-723`, `orders/models.py:138-141` | `select_for_update()` on the product inside the atomic block, deduct with `F("stock_quantity") - qty`. | Small |
| 3 | Receipt printing (up to 5 s of network I/O) happens inside the POS `transaction.atomic()`, holding the SQLite write lock for the whole store. | `pos/views.py:95` (open) to `:249` (print) | Move printing after the `with` block commits. | Small |
| 4 | SQLite is the production engine. One writer at a time; concurrent POS sales will hit "database is locked". | `settings.py:104` | Create a MySQL database in cPanel, set `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` in `.env`, add `mysqlclient` to requirements, `dumpdata` / `loaddata` to move rows. | Medium |
| 5 | Checkout creates the order, loops items, and deletes the cart with no transaction. A failure mid-loop leaves a half order and a gone cart. | `orders/views.py:48-70` | Wrap the POST branch in `transaction.atomic()`. | Small |
| 6 | Sale numbers and order numbers come from `Max()` / `order_by('-id').first()` with no lock, so concurrent sales can share a number. `Max` on an unindexed CharField also full-scans per sale. | `pos/models.py:495`, `orders/models.py:118-123` | Derive the number from the row's own `pk` after the first save, or keep a counter row read under `select_for_update()`. | Small |
| 7 | `DEBUG` defaults to `True` and `SECRET_KEY` to a public string. A missing `.env` on cPanel silently boots insecure. | `settings.py:23,26,28` | Default `DEBUG=False`; raise `ImproperlyConfigured` when `SECRET_KEY` is unset. | Small |
| 8 | `SiteSettings.objects.first()` can be `None` and is dereferenced without a guard, so a fresh deploy with no settings row fails every sale. The local also shadows Django's `settings`. | `pos/views.py:104,219` | `if site_settings and site_settings.printer_enabled`. | Trivial |
| 9 | Emails are sent synchronously inside requests and no `EMAIL_*` settings exist, so Django tries SMTP on localhost:25 and blocks until timeout. | `inventory/notifications.py:31,120,219`, `inventory/document_generation.py:204` | Configure cPanel SMTP in `.env`; send from a thread or a cron-driven management command. | Small |

## Tier 2: page speed for shoppers and cashiers

| # | Problem | Where | Fix | Effort |
|---|---------|-------|-----|--------|
| 10 | Tailwind is loaded as the runtime JIT compiler from a CDN (~400 KB, render-blocking, recompiles CSS in the browser on every page view). | `core/templates/base.html:43,55` | Build once with the Tailwind CLI into `core/static/css/tailwind.css` at deploy time. Removes the largest asset and the biggest first-paint delay. | Medium |
| 11 | No WhiteNoise and no hashed or compressed static storage. `main.css` and `main.js` ship uncompressed and uncacheable. With `DEBUG=False` under Passenger nothing serves static unless cPanel is hand-configured. | `settings.py` MIDDLEWARE, `requirements.txt` | Add `whitenoise`, `CompressedManifestStaticFilesStorage`, run `collectstatic` on deploy. | Small |
| 12 | Product list issues ~3 extra queries per card: `product.category` and `product.images.first` twice. About 36 extra queries per 12-item page. | `catalog/views.py:25`, `product_list.html:136-187` | `.select_related("category").prefetch_related("images")` and a `{% with %}` for the first image. | Small |
| 13 | POS product search re-queries barcodes per product twice, defeating the prefetch. Ranking runs in Python on `limit * 2` rows and `limit` is unbounded. | `pos/views.py:499-567` | `Prefetch("barcodes", queryset=Barcode.objects.filter(is_active=True))`, rank in SQL with `Case/When`, clamp `limit`. | Small |
| 14 | Search suggestion and API endpoints read `product.category.name` per row with no join. | `catalog/views.py:190-199,278-288` | Add `.select_related("category")`. | Trivial |
| 15 | Analytics dashboard runs 28 day-by-day queries in four loops. | `analytics/views.py:95-189` | One `TruncDate` + `annotate` query per metric. | Small |
| 16 | No lazy loading on any of the 25 `<img>` tags and no thumbnails; full-resolution uploads render into 192 px cards. | `catalog/models.py:106`, `product_list.html:139-143`, `home.html:269` | Add `loading="lazy" decoding="async"`; generate a thumbnail on upload with Pillow (already installed) or `django-imagekit`. | Small / Medium |
| 17 | `SiteSettings` is fetched from the DB on every request via the context processor. | `core/context_processors.py:14` | `cache.get_or_set("site_settings", ..., 300)` and clear it in `SiteSettings.save()`. Depends on item 1. | Trivial |
| 18 | Caching is effectively unused: one `cache_page` on robots.txt, no `{% cache %}` fragments, cache middleware configured but never added to `MIDDLEWARE`. | `settings.py:260-262`, templates | Fragment-cache the category nav and product grid keyed on filter params. Depends on item 1. | Small |
| 19 | Unbounded querysets rendered to templates: the whole catalog on the POS sale page and every product on stock movements. Category detail and related products are unpaginated and un-joined. | `pos/views.py:281`, `inventory/views.py:341`, `catalog/views.py:140-163` | Paginate or use the existing AJAX search endpoint. | Small |
| 20 | No `preconnect` for the three CDN origins and no `defer` on scripts. | `base.html` head | Add `<link rel="preconnect">` for Font Awesome and Google Fonts; `defer` Chart.js. | Trivial |

## Tier 3: operability

| # | Problem | Where | Fix |
|---|---------|-------|-----|
| 21 | No indexes on `created_at` or `status` for `Sales`, `Order`, `POSSale`, which every dashboard filters and sorts on. Inventory and catalog models do have indexes, so this is an inconsistency. | `analytics/models.py:78-81`, `orders/models.py:92-95`, `pos/models.py:476-479` | Add `Index(fields=["created_at"])` and `Index(fields=["status", "created_at"])`. |
| 22 | `/health/` returns a hardcoded timestamp string and catches only `OperationalError`. | `core/views.py:37-53` | `timezone.now()`, real `SELECT 1`, cache round-trip, catch `Exception`. Useful for a cPanel cron ping. |
| 23 | Logging uses a plain `FileHandler`: unbounded growth and interleaving across Passenger processes. | `settings.py:363-374` | `RotatingFileHandler` with `maxBytes` and `backupCount`. |
| 24 | Category admin list fires one `COUNT(*)` per row via the `product_count` property. | `catalog/admin.py:9,15` | Annotate `Count("products")` in `get_queryset`. |
| 25 | Test coverage: 15 tests total, none for POS, inventory, analytics, users, educational. The concurrency fixes in Tier 1 need tests to stay fixed. | `*/tests.py` | Start with POS sale creation, stock deduction, and checkout. |

## Suggested order of work

1. **Unblock production correctness first** (items 1, 7, 8): three small settings and guard changes that stop the site from failing outright with `DEBUG=False`.
2. **Protect stock and money** (items 2, 3, 5, 6): row locks, transaction boundaries, printing after commit. All small, all testable.
3. **Move off SQLite** (item 4) once the locking fixes are in, so the fixes are exercised by a real multi-writer database.
4. **Cut first-paint time** (items 10, 11, 16, 20): build Tailwind, add WhiteNoise, lazy-load and thumbnail images. This is the change shoppers will feel.
5. **Query hygiene** (items 12 to 15, 17 to 19, 21, 24): mechanical, low-risk, best done with `django-debug-toolbar` open to confirm query counts drop.
6. **Operability** (items 9, 22, 23, 25).

Each step above is small enough for its own data-safe deploy through the existing pull, migrate, restart routine on cPanel.


## Deploying these changes to cPanel

The app now refuses to start with `DEBUG=False` and no `SECRET_KEY`, so set the environment first.

1. Copy `.env.example` to `.env` in the app directory and fill in `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the database block, and the email block.
2. Install the two new packages and collect static files. In the cPanel Terminal with the app's virtualenv active:

```
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
mkdir -p cache logs
touch tmp/restart.txt
```

3. Open `/health/` and confirm `database` and `cache` both read `healthy`.
4. To move off SQLite: create a MySQL database and user in cPanel, put them in `.env`, then `python manage.py migrate` against the new database and `loaddata` a `dumpdata` export taken from the SQLite file. Do this in a quiet period; the POS writes stock on every sale.

Tailwind is compiled into `core/static/css/tailwind.css` and committed, so the server never needs Node. After editing templates locally run `npm install` once, then `npm run build:css` before deploying.

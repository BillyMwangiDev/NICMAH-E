"""
One-off: apply the inventory migrations (adds the Vaccines category) on the live
server. Run from Setup Python App > Execute python script, then restart the app.
Mirrors passenger_wsgi.py's environment setup so it hits the production database.
Writes its output to migrate_vaccines.log next to this file.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

log_path = BASE_DIR / "migrate_vaccines.log"
log = open(log_path, "a", encoding="utf-8")
sys.stdout = log
sys.stderr = log

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "agrovet.settings.production")

    # When run from the panel's "Execute python script", "localhost" resolves to
    # ::1 where PostgreSQL requires ident auth, which fails for this process.
    # The IPv4 loopback uses password auth. Override unless DB_HOST was set to
    # something other than localhost.
    # Both 127.0.0.1 and ::1 are ident-only on this host for the panel's script
    # runner, so use the local unix socket (empty host), which takes password auth.
    if os.environ.get("DB_HOST", "localhost") in ("localhost", "127.0.0.1"):
        os.environ["DB_HOST"] = os.environ.get("DB_HOST_OVERRIDE", "")

    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command

    print("settings:", settings.SETTINGS_MODULE, "db engine:", settings.DATABASES["default"]["ENGINE"],
          "host:", settings.DATABASES["default"]["HOST"])
    call_command("showmigrations", "inventory", verbosity=1)
    call_command("migrate", "inventory", verbosity=1)

    from inventory.models import Category
    vaccines = Category.objects.filter(slug="vaccines").first()
    print("vaccines:", vaccines, "| subcategories:",
          list(Category.objects.filter(parent=vaccines).values_list("slug", flat=True)) if vaccines else None)
    print("DONE OK")
except Exception as exc:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    print("DONE WITH ERROR:", exc)
finally:
    log.flush()
    log.close()

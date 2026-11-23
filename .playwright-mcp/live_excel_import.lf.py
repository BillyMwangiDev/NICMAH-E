import re
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models.signals import post_save
from django.utils.text import slugify

try:
    import pandas as pd
except ImportError:
    pd = None

from inventory.models import Category, Product

REQUIRED_COLUMNS = {"name", "category", "price", "stock", "unit"}

COLUMN_ALIASES = {
    # name
    "product name": "name",
    "product": "name",
    # category
    "category name": "category",
    # price
    "selling price": "price",
    "selling price (kes)": "price",
    "cost": "price",
    # stock
    "stock level": "stock",
    "stock qty": "stock",
    "quantity": "stock",
    "qty": "stock",
    # unit
    "unit of measure": "unit",
    "uom": "unit",
    # min/max stock
    "min stock": "minstock",
    "minimum stock": "minstock",
    "reorder point": "minstock",
    "max stock": "maxstock",
    "maximum stock": "maxstock",
    # supplier
    "supplier / brand": "supplier",
    "supplier/brand": "supplier",
    "brand": "supplier",
    # semen / AI
    "semen product?": "is_ai_product",
    "semen product": "is_ai_product",
    "is_ai": "is_ai_product",
    # sire code
    "sire code": "sire_code",
    # expiry
    "expiry": "expiry_date",
    "expiry date": "expiry_date",
}

UPDATE_FIELDS = [
    "price", "stock_level", "unit", "reorder_point", "max_stock",
    "supplier", "description", "is_ai_product", "breed", "origin_country", "is_active",
]


def _clean_col(c: str) -> str:
    c = str(c).strip()
    c = re.sub(r"\s*\*.*$", "", c)
    c = re.sub(r"\s*\(.*$", "", c)
    return c.strip().lower()


def _normalise_columns(df: "pd.DataFrame") -> "pd.DataFrame":
    df.columns = [_clean_col(c) for c in df.columns]
    df.rename(columns=COLUMN_ALIASES, inplace=True)
    return df


def _find_header_row(file_obj, max_rows: int = 6) -> int:
    for header_row in range(max_rows):
        try:
            file_obj.seek(0)
        except (AttributeError, OSError):
            pass
        test = pd.read_excel(file_obj, header=header_row, nrows=0, engine="openpyxl")
        aliased = {COLUMN_ALIASES.get(_clean_col(c), _clean_col(c)) for c in test.columns}
        if REQUIRED_COLUMNS.issubset(aliased):
            return header_row
    return 0


def import_products_from_excel(file_obj, *, suppress_stock_alerts: bool = True) -> dict:
    """
    Read an Excel or CSV file and bulk-upsert products.

    Optimised to use a single DB transaction and one SELECT query for all
    existing products — avoids per-row round-trips that cause server timeouts
    on large files.

    Returns: {"imported": N, "skipped": M, "errors": [{"row": N, "error": str}]}
    """
    if pd is None:
        return {
            "imported": 0,
            "skipped": 0,
            "errors": [{"row": 0, "error": "Excel/CSV import requires 'pandas' and 'openpyxl'."}],
        }

    file_name = getattr(file_obj, "name", "").lower()

    try:
        if file_name.endswith(".csv"):
            df = pd.read_csv(file_obj)
        else:
            header_row = _find_header_row(file_obj)
            try:
                file_obj.seek(0)
            except (AttributeError, OSError):
                pass
            df = pd.read_excel(file_obj, header=header_row, engine="openpyxl")
    except Exception as exc:
        return {"imported": 0, "skipped": 0, "errors": [{"row": 0, "error": f"Could not read file: {exc}"}]}

    df = _normalise_columns(df)

    if "name" in df.columns:
        name_col = df["name"].astype(str).str.strip()
        df = df[~name_col.str.startswith("▸")]
        df = df[~name_col.str.startswith("▶")]
        df = df[~name_col.str.lower().str.startswith("required")]
        df = df[~name_col.str.lower().str.startswith("fill in")]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return {
            "imported": 0,
            "skipped": 0,
            "errors": [{"row": 0, "error": (
                f"Missing required columns: {', '.join(sorted(missing))}. "
                f"Found: {', '.join(sorted(df.columns))}"
            )}],
        }

    results = {"imported": 0, "skipped": 0, "errors": []}

    # ── Phase 1: Parse all rows up front (no DB calls) ────────────────────────
    parsed = []
    for idx, row in df.iterrows():
        row_num = idx + 2
        name = _clean_str(row.get("name", ""))
        category_name = _clean_str(row.get("category", ""))
        unit = _clean_str(row.get("unit", ""))

        if not name or not category_name or not unit:
            results["errors"].append({"row": row_num, "error": "Name, category and unit are required."})
            results["skipped"] += 1
            continue

        try:
            price = Decimal(str(row["price"]).replace(",", "").strip())
        except (InvalidOperation, ValueError):
            results["errors"].append({"row": row_num, "error": f"Invalid price: {row.get('price')}"})
            results["skipped"] += 1
            continue
        if price < 0:
            results["errors"].append({"row": row_num, "error": "Price cannot be negative."})
            results["skipped"] += 1
            continue

        try:
            stock_level = int(float(str(row.get("stock", 0)).replace(",", "").strip()))
        except (ValueError, TypeError):
            results["errors"].append({"row": row_num, "error": f"Invalid stock quantity: {row.get('stock')}"})
            results["skipped"] += 1
            continue
        if stock_level < 0:
            results["errors"].append({"row": row_num, "error": "Stock quantity cannot be negative."})
            results["skipped"] += 1
            continue

        reorder_point = _safe_int(row.get("minstock"), default=10)
        max_stock = _safe_int(row.get("maxstock"), default=100)
        if reorder_point < 0 or max_stock < 0:
            results["errors"].append({"row": row_num, "error": "Min stock and max stock cannot be negative."})
            results["skipped"] += 1
            continue

        parsed.append({
            "row_num": row_num,
            "name": name,
            "category_name": category_name,
            "price": price,
            "stock_level": stock_level,
            "unit": unit,
            "reorder_point": reorder_point,
            "max_stock": max_stock,
            "supplier": _clean_str(row.get("supplier", "")),
            "description": _clean_str(row.get("description", "")),
            "is_ai_product": _clean_str(row.get("is_ai_product", "false")).lower() in ("true", "1", "yes"),
            "breed": _clean_str(row.get("breed", "")),
            "origin_country": _clean_str(row.get("origin_country", "")),
            "sire_code": _clean_str(row.get("sire_code", "")) or None,
        })

    if not parsed:
        return results

    # ── Phase 2: All DB work in a single transaction ───────────────────────────
    try:
        with _stock_alerts_suppressed(enabled=suppress_stock_alerts):
            _upsert_all(parsed, results)
    except Exception as exc:
        results["errors"].append({"row": 0, "error": f"Bulk import failed: {exc}"})

    return results


@transaction.atomic
def _upsert_all(parsed: list, results: dict) -> None:
    # Get or create categories — at most one query per unique category name
    category_names = {r["category_name"] for r in parsed}
    category_map: dict = {}
    for cat_name in category_names:
        cat, _ = Category.objects.get_or_create(
            slug=slugify(cat_name) or "category",
            defaults={"name": cat_name.title()},
        )
        category_map[cat_name] = cat

    # Load ALL existing products in one query
    existing: dict = {
        (p.name, p.category_id): p
        for p in Product.objects.all()
    }

    for r in parsed:
        try:
            cat = category_map[r["category_name"]]
            key = (r["name"], cat.id)

            fields = {
                "price": r["price"],
                "stock_level": r["stock_level"],
                "unit": r["unit"],
                "reorder_point": r["reorder_point"],
                "max_stock": r["max_stock"],
                "supplier": r["supplier"],
                "description": r["description"],
                "is_ai_product": r["is_ai_product"],
                "breed": r["breed"],
                "origin_country": r["origin_country"],
                "is_active": True,
            }
            if r["sire_code"]:
                fields["sire_code"] = r["sire_code"]

            if key in existing:
                p = existing[key]
                for field, value in fields.items():
                    setattr(p, field, value)
                p.save(update_fields=list(fields.keys()))
            else:
                Product.objects.create(name=r["name"], category=cat, **fields)

            results["imported"] += 1

        except Exception as exc:
            results["errors"].append({"row": r["row_num"], "error": str(exc)})
            results["skipped"] += 1


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (ValueError, TypeError):
        return default


def _clean_str(value, default: str = "") -> str:
    s = str(value).strip()
    return default if s.lower() in ("nan", "none", "nat", "") else s


@contextmanager
def _stock_alerts_suppressed(enabled: bool = True):
    if not enabled:
        yield
        return

    from inventory.signals import handle_product_stock_alerts

    disconnected = post_save.disconnect(handle_product_stock_alerts, sender=Product)
    try:
        yield
    finally:
        if disconnected:
            post_save.connect(handle_product_stock_alerts, sender=Product)

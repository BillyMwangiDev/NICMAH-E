import os
from django.core.management.base import BaseCommand
from inventory.services.excel_import import import_products_from_excel

EXCEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "import_data.xlsx"
)


class Command(BaseCommand):
    help = "Import products from import_data.xlsx in the backend/ folder (signals suppressed)"

    def handle(self, *args, **options):
        path = os.path.abspath(EXCEL_PATH)
        if not os.path.exists(path):
            self.stderr.write(f"File not found: {path}")
            self.stderr.write("Upload import_data.xlsx to the backend/ folder.")
            return

        self.stdout.write(f"Importing from: {path}")
        self.stdout.write("Stock alert emails suppressed for bulk import.")

        class FileWrapper:
            def __init__(self, p):
                self._f = open(p, "rb")
                self.name = p
            def read(self, *a): return self._f.read(*a)
            def seek(self, *a): return self._f.seek(*a)
            def tell(self): return self._f.tell()
            def seekable(self): return True
            def readable(self): return True
            def close(self): self._f.close()

        f = FileWrapper(path)
        try:
            result = import_products_from_excel(f, suppress_stock_alerts=True)
        finally:
            f.close()

        self.stdout.write(f"Imported : {result['imported']}")
        self.stdout.write(f"Skipped  : {result['skipped']}")
        self.stdout.write(f"Errors   : {len(result['errors'])}")
        for e in result["errors"][:20]:
            self.stdout.write(f"  Row {e['row']}: {e['error']}")

        if result["imported"] > 0:
            self.stdout.write(self.style.SUCCESS("Import complete!"))

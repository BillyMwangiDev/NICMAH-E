"""
Upload-time image shrinking.

Product photos are uploaded straight from phones at 3000+ px and then rendered
into 200 px cards. Downsizing once on save keeps every later page load small.
"""

import logging
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

MAX_SIDE = 1200
JPEG_QUALITY = 82


def shrink_image_field(field_file, max_side=MAX_SIDE):
    """Downsize an ImageFieldFile in place if either side exceeds max_side.

    Returns True when the file was replaced. Safe to call on an empty field or
    an already-saved file; any Pillow failure is logged and the original kept.
    """
    if not field_file or not getattr(field_file, "file", None):
        return False
    try:
        field_file.open()
        with Image.open(field_file) as img:
            if max(img.size) <= max_side:
                return False
            img = ImageOps.exif_transpose(img)
            img.thumbnail((max_side, max_side), Image.LANCZOS)
            fmt = (img.format or "JPEG").upper()
            buf = BytesIO()
            if fmt in ("JPEG", "JPG"):
                img.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            elif fmt == "PNG":
                img.save(buf, format="PNG", optimize=True)
            else:
                img.save(buf, format=fmt)
        name = field_file.name.rsplit("/", 1)[-1]
        field_file.save(name, ContentFile(buf.getvalue()), save=False)
        return True
    except Exception:
        logger.exception("Could not shrink uploaded image %s", getattr(field_file, "name", "?"))
        return False

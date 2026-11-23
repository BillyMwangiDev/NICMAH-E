"""
Non-blocking email helper.

Stock alerts and similar notifications must never hold a web request open while
an SMTP server is slow or unreachable. This sends in a daemon thread and logs
failures instead of raising.
"""

import logging
import threading

from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _send(kwargs):
    try:
        send_mail(**kwargs)
    except Exception:
        logger.exception("Background email to %s failed", kwargs.get("recipient_list"))


def send_mail_async(**kwargs):
    """Queue send_mail(**kwargs) on a background thread and return it.

    The returned thread lets callers (and tests) join() it when they need the
    message to have been handed to the backend.
    """
    kwargs.setdefault("fail_silently", False)
    thread = threading.Thread(target=_send, args=(kwargs,), daemon=True)
    thread.start()
    return thread

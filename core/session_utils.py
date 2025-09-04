"""
Custom session utilities for shorter session IDs.
"""
import random
import string
from django.contrib.sessions.backends.db import SessionStore


def generate_short_session_key():
    """Generate a shorter session key (12 characters instead of default 32)."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))


class ShortSessionStore(SessionStore):
    """Session store that generates shorter session keys."""
    
    def _get_new_session_key(self):
        """Generate a shorter session key (12 characters instead of default 32)."""
        while True:
            session_key = generate_short_session_key()
            if not self.exists(session_key):
                return session_key

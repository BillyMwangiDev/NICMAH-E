"""
App configuration for nichmah_agrovet project.
"""

from django.apps import AppConfig


class NichmahAgrovetConfig(AppConfig):
    """Configuration for the nichmah_agrovet Django app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'nichmah_agrovet'
    verbose_name = 'NICMAH Core'

    def ready(self):
        """Import signals when the app is ready."""
        try:
            import nichmah_agrovet.signals  # noqa: F401
        except ImportError:
            pass


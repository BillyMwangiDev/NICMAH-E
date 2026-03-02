"""
Security signals for NICMAH-E Django application.
Handles security event logging via Django signals.
"""

from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .security_settings import log_security_event
from .security_middleware import get_client_ip

User = get_user_model()


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request=None, **kwargs):
    """Log failed login attempts when Django auth system reports them."""
    username = credentials.get('username', 'unknown')
    ip_address = get_client_ip(request) if request else 'unknown'
    
    log_security_event(
        'FAILED_LOGIN',
        f'Failed login attempt for user: {username}',
        user_id=None,  # User not authenticated, so no user_id
        ip_address=ip_address
    )


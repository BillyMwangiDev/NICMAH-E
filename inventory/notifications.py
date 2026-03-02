"""
Stock notification service for NICMAH application.
Handles email, SMS, and in-app notifications for stock alerts.
"""

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.utils import timezone
from .models import StockAlert, NotificationPreference
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class StockNotificationService:
    """Service class for handling stock notifications"""

    def __init__(self):
        self.email_enabled = getattr(settings, "EMAIL_ENABLED", True)
        self.sms_enabled = getattr(settings, "SMS_ENABLED", False)

    def send_stock_alert_notification(self, stock_alert):
        """Send notifications for a stock alert"""
        try:
            # Get users who should receive this notification
            users_to_notify = self._get_users_to_notify(stock_alert)

            for user in users_to_notify:
                self._send_user_notification(user, stock_alert)

            logger.info(
                f"Sent stock alert notifications to {len(users_to_notify)} users for {stock_alert.product.name}"
            )

        except Exception as e:
            logger.error(f"Error sending stock alert notification: {str(e)}")

    def _get_users_to_notify(self, stock_alert):
        """Get users who should receive notifications for this alert"""
        users = []

        # Get users with notification preferences
        notification_prefs = NotificationPreference.objects.filter(user__is_active=True)

        for pref in notification_prefs:
            if self._should_notify_user(pref, stock_alert):
                users.append(pref.user)

        # Also notify admin users
        admin_users = User.objects.filter(is_active=True, role__in=["admin", "manager"])

        for admin_user in admin_users:
            if admin_user not in users:
                users.append(admin_user)

        return users

    def _should_notify_user(self, notification_pref, stock_alert):
        """Check if user should be notified based on preferences"""
        if stock_alert.alert_type == "low_stock" and notification_pref.low_stock_alerts:
            return True
        elif stock_alert.alert_type == "out_of_stock" and notification_pref.out_of_stock_alerts:
            return True
        elif stock_alert.alert_type == "expiring_soon" and notification_pref.expiring_soon_alerts:
            return True
        elif stock_alert.alert_type == "overstock" and notification_pref.overstock_alerts:
            return True
        elif stock_alert.alert_type == "slow_moving" and notification_pref.slow_moving_alerts:
            return True

        return False

    def _send_user_notification(self, user, stock_alert):
        """Send notification to a specific user"""
        try:
            # Get user's notification preferences
            notification_pref = getattr(user, "notification_preferences", None)

            if not notification_pref:
                # Create default preferences
                notification_pref = NotificationPreference.objects.create(user=user)

            # Send email notification
            if notification_pref.email_notifications and self.email_enabled:
                self._send_email_notification(user, stock_alert)

            # Send SMS notification
            if notification_pref.sms_notifications and self.sms_enabled:
                self._send_sms_notification(user, stock_alert)

            # Send in-app notification
            if notification_pref.in_app_notifications:
                self._send_in_app_notification(user, stock_alert)

        except Exception as e:
            logger.error(f"Error sending notification to user {user.username}: {str(e)}")

    def _send_email_notification(self, user, stock_alert):
        """Send email notification"""
        try:
            subject = f"Stock Alert: {stock_alert.get_alert_type_display()} - {stock_alert.product.name}"

            # Prepare email context
            context = {
                "user": user,
                "stock_alert": stock_alert,
                "product": stock_alert.product,
                "site_name": getattr(settings, "SITE_NAME", "NICMAH"),
                "alert_date": timezone.now().strftime("%B %d, %Y at %I:%M %p"),
            }

            # Render email templates
            html_message = render_to_string("inventory/emails/stock_alert.html", context)
            plain_message = render_to_string("inventory/emails/stock_alert.txt", context)

            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Email notification sent to {user.email} for stock alert {stock_alert.alert_id}")

        except Exception as e:
            logger.error(f"Error sending email notification to {user.email}: {str(e)}")

    def _send_sms_notification(self, user, stock_alert):
        """Send SMS notification"""
        try:
            # This would integrate with an SMS service like Twilio
            # For now, just log the attempt
            message = f"Stock Alert: {stock_alert.product.name} - {stock_alert.message}"

            logger.info(f"SMS notification would be sent to {user.phone}: {message}")

            # SMS sending implementation placeholder
            # To implement: Integrate with SMS service provider (Twilio, Africa's Talking, etc.)
            # Example with Twilio:
            # from twilio.rest import Client
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # client.messages.create(
            #     body=message,
            #     from_=settings.TWILIO_PHONE_NUMBER,
            #     to=user.phone
            # )

        except Exception as e:
            logger.error(f"Error sending SMS notification to {user.username}: {str(e)}")

    def _send_in_app_notification(self, user, stock_alert):
        """Send in-app notification"""
        try:
            # This would create a notification record in the database
            # For now, just log the attempt
            notification_data = {
                "user": user,
                "title": f"Stock Alert: {stock_alert.get_alert_type_display()}",
                "message": stock_alert.message,
                "alert_type": "stock_alert",
                "related_object_id": stock_alert.id,
                "related_object_type": "StockAlert",
            }

            logger.info(f"In-app notification would be created for {user.username}: {notification_data}")

            # In-app notification system placeholder
            # To implement: Create Notification model and system
            # Example:
            # from notifications.models import Notification
            # Notification.objects.create(**notification_data)

        except Exception as e:
            logger.error(f"Error creating in-app notification for {user.username}: {str(e)}")

    def send_bulk_notifications(self, alerts):
        """Send notifications for multiple alerts"""
        for alert in alerts:
            self.send_stock_alert_notification(alert)

    def send_daily_summary(self, user):
        """Send daily summary of stock alerts"""
        try:
            # Get today's alerts for the user
            today = timezone.now().date()
            alerts = StockAlert.objects.filter(created_at__date=today, product__in=user.get_accessible_products())

            if not alerts.exists():
                return

            # Send summary email
            if self.email_enabled:
                self._send_daily_summary_email(user, alerts)

        except Exception as e:
            logger.error(f"Error sending daily summary to {user.username}: {str(e)}")

    def _send_daily_summary_email(self, user, alerts):
        """Send daily summary email"""
        try:
            subject = f"Daily Stock Alert Summary - {timezone.now().strftime('%B %d, %Y')}"

            context = {
                "user": user,
                "alerts": alerts,
                "site_name": getattr(settings, "SITE_NAME", "NICMAH"),
                "date": timezone.now().strftime("%B %d, %Y"),
            }

            html_message = render_to_string("inventory/emails/daily_summary.html", context)
            plain_message = render_to_string("inventory/emails/daily_summary.txt", context)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Daily summary email sent to {user.email}")

        except Exception as e:
            logger.error(f"Error sending daily summary email to {user.email}: {str(e)}")


class StockAlertManager:
    """Manager class for handling stock alerts"""

    @staticmethod
    def create_low_stock_alert(product, current_stock, threshold):
        """Create a low stock alert"""
        alert, created = StockAlert.objects.get_or_create(
            product=product,
            alert_type="low_stock",
            defaults={
                "current_value": current_stock,
                "threshold_value": threshold,
                "message": f"Low stock alert: {product.name} - Current: {current_stock}, Threshold: {threshold}",
                "priority": "high" if current_stock == 0 else "medium",
            },
        )

        if not created:
            # Update existing alert
            alert.current_value = current_stock
            alert.message = f"Low stock alert: {product.name} - Current: {current_stock}, Threshold: {threshold}"
            alert.priority = "high" if current_stock == 0 else "medium"
            alert.save()

        return alert

    @staticmethod
    def create_expiring_soon_alert(product, expiry_date):
        """Create an expiring soon alert"""
        days_until_expiry = (expiry_date - timezone.now().date()).days

        if days_until_expiry <= 30:  # Alert if expiring within 30 days
            alert, created = StockAlert.objects.get_or_create(
                product=product,
                alert_type="expiring_soon",
                defaults={
                    "current_value": days_until_expiry,
                    "threshold_value": 30,
                    "message": f"Product expiring soon: {product.name} expires in {days_until_expiry} days",
                    "priority": "high" if days_until_expiry <= 7 else "medium",
                },
            )

            if not created:
                alert.current_value = days_until_expiry
                alert.message = f"Product expiring soon: {product.name} expires in {days_until_expiry} days"
                alert.priority = "high" if days_until_expiry <= 7 else "medium"
                alert.save()

            return alert

        return None

    @staticmethod
    def resolve_alert(alert, user):
        """Resolve a stock alert"""
        alert.resolve(user)

        # Send resolution notification
        notification_service = StockNotificationService()
        notification_service._send_alert_resolution_notification(user, alert)

    @staticmethod
    def get_active_alerts():
        """Get all active stock alerts"""
        return StockAlert.objects.filter(status="active")

    @staticmethod
    def get_critical_alerts():
        """Get critical priority alerts"""
        return StockAlert.objects.filter(status="active", priority="critical")

    @staticmethod
    def cleanup_resolved_alerts():
        """Clean up old resolved alerts"""
        from datetime import timedelta

        # Delete alerts resolved more than 30 days ago
        cutoff_date = timezone.now() - timedelta(days=30)
        StockAlert.objects.filter(status="resolved", resolved_at__lt=cutoff_date).delete()

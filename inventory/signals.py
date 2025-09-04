"""
Signals for inventory management.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import StockMovement, StockAlert, NotificationPreference
from catalog.models import Product
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=User)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    """Create notification preferences for new users."""
    if created:
        NotificationPreference.objects.create(user=instance)
        logger.info(f"Created notification preferences for user: {instance.username}")


@receiver(post_save, sender=StockMovement)
def check_stock_levels_after_movement(sender, instance, created, **kwargs):
    """Check stock levels after stock movement and generate alerts if needed."""
    if created:
        product = instance.product
        current_stock = product.stock_quantity

        # Check if stock is low (below reorder level)
        reorder_level = getattr(product, "reorder_level", 5)  # Default to 5 if not set

        # Generate low stock alert
        if current_stock <= reorder_level:
            alert, created = StockAlert.objects.get_or_create(
                product=product,
                alert_type=StockAlert.AlertType.LOW_STOCK,
                defaults={
                    "current_value": current_stock,
                    "threshold_value": reorder_level,
                    "message": (
                        f"Low stock alert: {product.name} - Current: {current_stock}, " f"Threshold: {reorder_level}"
                    ),
                    "priority": "high" if current_stock == 0 else "medium",
                },
            )

            if not created:
                # Update existing alert
                alert.current_value = current_stock
                alert.message = (
                    f"Low stock alert: {product.name} - Current: {current_stock}, Threshold: {reorder_level}"
                )
                alert.priority = "high" if current_stock == 0 else "medium"
                alert.save()

            logger.info(f"Generated low stock alert for {product.name}")

        # Generate out of stock alert
        if current_stock == 0:
            alert, created = StockAlert.objects.get_or_create(
                product=product,
                alert_type=StockAlert.AlertType.OUT_OF_STOCK,
                defaults={
                    "current_value": current_stock,
                    "threshold_value": 0,
                    "message": f"Out of stock alert: {product.name}",
                    "priority": "critical",
                },
            )

            if not created:
                # Update existing alert
                alert.current_value = current_stock
                alert.save()

            logger.info(f"Generated out of stock alert for {product.name}")


@receiver(post_save, sender=Product)
def check_product_stock_on_save(sender, instance, created, **kwargs):
    """Check stock levels when product is saved and generate alerts if needed."""
    current_stock = instance.stock_quantity
    reorder_level = getattr(instance, "reorder_level", 5)

    # Generate low stock alert
    if current_stock <= reorder_level:
        alert, created = StockAlert.objects.get_or_create(
            product=instance,
            alert_type=StockAlert.AlertType.LOW_STOCK,
            defaults={
                "current_value": current_stock,
                "threshold_value": reorder_level,
                "message": f"Low stock alert: {instance.name} - Current: {current_stock}, Threshold: {reorder_level}",
                "priority": "high" if current_stock == 0 else "medium",
            },
        )

        if not created:
            # Update existing alert
            alert.current_value = current_stock
            alert.message = f"Low stock alert: {instance.name} - Current: {current_stock}, Threshold: {reorder_level}"
            alert.priority = "high" if current_stock == 0 else "medium"
            alert.save()

    # Generate out of stock alert
    if current_stock == 0:
        alert, created = StockAlert.objects.get_or_create(
            product=instance,
            alert_type=StockAlert.AlertType.OUT_OF_STOCK,
            defaults={
                "current_value": current_stock,
                "threshold_value": 0,
                "message": f"Out of stock alert: {instance.name}",
                "priority": "critical",
            },
        )

        if not created:
            # Update existing alert
            alert.current_value = current_stock
            alert.save()


@receiver(post_delete, sender=StockAlert)
def log_alert_deletion(sender, instance, **kwargs):
    """Log when stock alerts are deleted."""
    logger.info(f"Stock alert deleted for {instance.product.name}: {instance.alert_type}")

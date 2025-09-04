"""
Common mixins for models to eliminate duplicate code.
"""

from django.db import models


class TimestampMixin(models.Model):
    """Mixin to add created_at and updated_at fields to models."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class StatusMixin(models.Model):
    """Mixin to add status field with choices to models."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        abstract = True


class NameSlugMixin(models.Model):
    """Mixin to add name and slug fields to models."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class DescriptionMixin(models.Model):
    """Mixin to add description field to models."""

    description = models.TextField(blank=True)

    class Meta:
        abstract = True


class IsActiveMixin(models.Model):
    """Mixin to add is_active field to models."""

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class OrderingMixin(models.Model):
    """Mixin to add ordering field to models."""

    order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["order"]


class AuditMixin(models.Model):
    """Mixin to add audit fields to models."""

    created_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_created"
    )
    updated_by = models.ForeignKey(
        "users.CustomUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="%(class)s_updated"
    )

    class Meta:
        abstract = True

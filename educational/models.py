"""
Educational content models for Nichmah Agrovet application.
"""

from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    """Article category model."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="FontAwesome icon class")
    color = models.CharField(max_length=20, default="green", help_text="Tailwind color class")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "category"
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("educational:category_detail", kwargs={"slug": self.slug})


class Article(models.Model):
    """Educational article model."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True, help_text="Brief summary of the article")
    # Temporarily using CharField to match current database
    category = models.CharField(max_length=100, blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, related_name="articles", blank=True, null=True
    )
    image = models.CharField(max_length=100, blank=True, null=True)  # Match current database field name
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "article"
        verbose_name_plural = "articles"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("educational:article_detail", kwargs={"slug": self.slug})

    def increment_view_count(self):
        """Increment the view count."""
        self.view_count += 1
        self.save(update_fields=["view_count"])

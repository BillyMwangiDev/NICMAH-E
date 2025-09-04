"""
Common view mixins to eliminate duplicate code across views.py files.
"""

from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.db.models import Q


class BaseViewMixin:
    """Base mixin for common view functionality."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = getattr(self, "page_title", self.model._meta.verbose_name_plural.title())
        return context

    def form_valid(self, form):
        messages.success(self.request, f"{self.model._meta.verbose_name.title()} saved successfully.")
        return super().form_valid(form)

    def delete(self, request, *args, **kwargs):
        messages.success(request, f"{self.model._meta.verbose_name.title()} deleted successfully.")
        return super().delete(request, *args, **kwargs)


class SearchMixin:
    """Mixin to add search functionality to views."""

    search_fields = ["name", "description"]

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            query = Q()
            for field in self.search_fields:
                if hasattr(self.model, field):
                    query |= Q(**{f"{field}__icontains": q})
            queryset = queryset.filter(query)
        return queryset


class FilterMixin:
    """Mixin to add filtering functionality to views."""

    filter_fields = []

    def get_queryset(self):
        queryset = super().get_queryset()
        for field in self.filter_fields:
            value = self.request.GET.get(field)
            if value and hasattr(self.model, field):
                queryset = queryset.filter(**{field: value})
        return queryset


class PaginationMixin:
    """Mixin to add pagination to views."""

    paginate_by = 20

    def get_paginate_by(self, queryset):
        return self.request.GET.get("paginate_by", self.paginate_by)


class PermissionMixin:
    """Mixin to add permission checking to views."""

    permission_required = None
    login_url = "/users/login/"

    def dispatch(self, request, *args, **kwargs):
        if self.permission_required and not request.user.has_perm(self.permission_required):
            messages.error(request, "You do not have permission to access this page.")
            return redirect(self.login_url)
        return super().dispatch(request, *args, **kwargs)


class AjaxMixin:
    """Mixin to handle AJAX requests."""

    def is_ajax(self):
        return self.request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def ajax_response(self, data, status=200):
        return JsonResponse(data, status=status)


class MessageMixin:
    """Mixin to add message functionality to views."""

    success_message = ""
    error_message = ""

    def add_message(self, message, level="success"):
        if message:
            messages.add_message(self.request, getattr(messages, level.upper()), message)

    def form_valid(self, form):
        response = super().form_valid(form)
        self.add_message(self.success_message)
        return response

    def form_invalid(self, form):
        self.add_message(self.error_message, "error")
        return super().form_invalid(form)


class ContextMixin:
    """Mixin to add common context to views."""

    extra_context = {}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.extra_context)
        return context


class TemplateMixin:
    """Mixin to customize template names."""

    template_name_suffix = "_detail"

    def get_template_names(self):
        names = super().get_template_names()
        if hasattr(self, "custom_template_name"):
            names.insert(0, self.custom_template_name)
        return names


class SuccessUrlMixin:
    """Mixin to customize success URLs."""

    def get_success_url(self):
        if hasattr(self, "success_url"):
            return self.success_url
        if hasattr(self, "object") and self.object:
            return self.object.get_absolute_url()
        return reverse_lazy("home")


class FormMixin:
    """Mixin to customize form handling."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

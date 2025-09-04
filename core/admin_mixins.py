"""
Common admin mixins to eliminate duplicate code across admin.py files.
"""


class TimestampAdminMixin:
    """Mixin to add common timestamp fields to admin."""

    readonly_fields = ["created_at", "updated_at"]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj:  # Editing existing object
            readonly.extend(["created_at"])
        return readonly


class StatusFilterMixin:
    """Mixin to add common status filters to admin."""

    list_filter = ["status", "is_active"]

    def get_list_filter(self, request):
        list_filter = list(super().get_list_filter(request))
        # Add status fields if they exist
        if hasattr(self.model, "status"):
            if "status" not in list_filter:
                list_filter.append("status")
        if hasattr(self.model, "is_active"):
            if "is_active" not in list_filter:
                list_filter.append("is_active")
        return list_filter


class SearchMixin:
    """Mixin to add common search fields to admin."""

    search_fields = ["name", "description"]

    def get_search_fields(self, request):
        search_fields = list(super().get_search_fields(request))
        # Add common search fields if they exist
        if hasattr(self.model, "name") and "name" not in search_fields:
            search_fields.append("name")
        if hasattr(self.model, "description") and "description" not in search_fields:
            search_fields.append("description")
        return search_fields


class OrderingMixin:
    """Mixin to add common ordering to admin."""

    ordering = ["-created_at"]

    def get_ordering(self, request):
        ordering = list(super().get_ordering(request))
        # Add created_at ordering if it exists
        if hasattr(self.model, "created_at") and "-created_at" not in ordering:
            ordering.insert(0, "-created_at")
        return ordering


class ActionMixin:
    """Mixin to add common admin actions."""

    actions = ["mark_active", "mark_inactive"]

    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} items marked as active.")

    mark_active.short_description = "Mark selected items as active"

    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} items marked as inactive.")

    mark_inactive.short_description = "Mark selected items as inactive"


class ExportMixin:
    """Mixin to add export functionality to admin."""

    actions = ["export_as_csv"]

    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={meta.verbose_name_plural}.csv"
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field)
                if callable(value):
                    value = value()
                row.append(str(value))
            writer.writerow(row)

        return response

    export_as_csv.short_description = "Export selected items as CSV"


class ReadOnlyMixin:
    """Mixin to make admin read-only."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AuditMixin:
    """Mixin to add audit fields to admin."""

    readonly_fields = ["created_by", "updated_by", "created_at", "updated_at"]

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

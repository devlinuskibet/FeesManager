"""Read-only Django admin registration for LedgerEntry."""

from django.contrib import admin

from .models import LedgerEntry


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    """Expose ledger entries in admin as strictly read-only."""

    list_display = ("student", "term", "entry_type", "direction", "amount", "created_at")
    list_filter = ("school", "entry_type", "direction")
    search_fields = ("student__admission_number", "reference")

    def has_add_permission(self, request):
        """Ledger entries must be created via services, never manually in admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """Ledger entries are append-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Ledger entries cannot be deleted."""
        return False

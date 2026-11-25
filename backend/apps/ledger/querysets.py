"""Append-only, tenant-scoped queryset and manager for LedgerEntry."""

from apps.tenants.managers import TenantQuerySet

from .exceptions import LedgerImmutableError


class LedgerEntryQuerySet(TenantQuerySet):
    """TenantQuerySet subclass that blocks mutations and validates bulk inserts."""

    def update(self, **kwargs):
        """Block bulk SQL updates on ledger entries."""
        raise LedgerImmutableError.for_operation("update")

    def delete(self):
        """Block queryset-level deletes on ledger entries."""
        raise LedgerImmutableError.for_operation("delete")

    def bulk_update(self, objs, fields, batch_size=None):
        """Block bulk_update on ledger entries."""
        raise LedgerImmutableError.for_operation("bulk_update")

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        """Validate every object via full_clean() before bulk insert; forbid upsert conflicts."""
        if update_conflicts:
            raise LedgerImmutableError.for_operation("update_conflicts")
        # Materialize generator/iterable so we can validate every instance before DB write.
        validated_objs = list(objs)
        for obj in validated_objs:
            obj.full_clean()
        return super().bulk_create(
            validated_objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )


# Manager built from LedgerEntryQuerySet so .for_school() and immutability rules apply everywhere.
LedgerEntryManager = LedgerEntryQuerySet.as_manager()

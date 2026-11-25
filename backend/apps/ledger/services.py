"""Transactional services for posting and reversing ledger entries."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from .models import LedgerEntry


def post_entry(
    *,
    school,
    student,
    term,
    entry_type,
    direction,
    amount,
    created_by=None,
    reason="",
    reference="",
    source_type="",
    source_id=None,
) -> LedgerEntry:
    """Atomically create and validate a new LedgerEntry."""
    with transaction.atomic():
        return LedgerEntry.objects.create(
            school=school,
            student=student,
            term=term,
            entry_type=entry_type,
            direction=direction,
            amount=amount,
            created_by=created_by,
            reason=reason,
            reference=reference,
            source_type=source_type,
            source_id=source_id,
        )


def reverse_entry(entry: LedgerEntry, *, created_by, reason: str) -> LedgerEntry:
    """Atomically create an opposite-direction reversal for an existing LedgerEntry."""
    if not (reason or "").strip():
        raise ValidationError(_("A non-empty reason is required to reverse an entry."))

    with transaction.atomic():
        # Lock the target row so concurrent reversals cannot both pass the pre-check.
        original = LedgerEntry.objects.select_for_update().get(pk=entry.pk)
        if original.entry_type == LedgerEntry.EntryType.REVERSAL:
            raise ValidationError(_("Cannot reverse a reversal entry."))
        if hasattr(original, "reversed_by"):
            raise ValidationError(_("Entry has already been reversed."))

        opposite_direction = (
            LedgerEntry.Direction.CREDIT
            if original.direction == LedgerEntry.Direction.DEBIT
            else LedgerEntry.Direction.DEBIT
        )
        return LedgerEntry.objects.create(
            school=original.school,
            student=original.student,
            term=original.term,
            entry_type=LedgerEntry.EntryType.REVERSAL,
            direction=opposite_direction,
            amount=original.amount,
            reverses=original,
            created_by=created_by,
            reason=reason,
            reference=original.reference,
            source_type=original.source_type,
            source_id=original.source_id,
        )

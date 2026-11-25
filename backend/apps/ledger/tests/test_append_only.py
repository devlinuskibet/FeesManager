"""Tests for append-only immutability and PROTECT foreign keys on LedgerEntry."""

from decimal import Decimal

import pytest
from django.db.models import ProtectedError

from apps.ledger.exceptions import LedgerImmutableError
from apps.ledger.models import LedgerEntry
from apps.ledger.services import post_entry


@pytest.mark.django_db
def test_save_existing_entry_raises(school, student, term):
    """Updating an existing LedgerEntry via save() raises LedgerImmutableError."""
    entry = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("500.00"),
    )
    entry.amount = Decimal("600.00")
    with pytest.raises(LedgerImmutableError, match="append-only"):
        entry.save()


@pytest.mark.django_db
def test_instance_delete_raises(school, student, term):
    """Calling delete() on a LedgerEntry raises LedgerImmutableError."""
    entry = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("500.00"),
    )
    with pytest.raises(LedgerImmutableError, match="append-only"):
        entry.delete()


@pytest.mark.django_db
def test_queryset_update_delete_bulk_update_raise(school, student, term):
    """QuerySet.update(), delete(), and bulk_update() all raise LedgerImmutableError."""
    entry = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("500.00"),
    )
    qs = LedgerEntry.objects.for_school(school)
    with pytest.raises(LedgerImmutableError, match="append-only"):
        qs.update(amount=Decimal("100.00"))
    with pytest.raises(LedgerImmutableError, match="append-only"):
        qs.delete()
    entry.amount = Decimal("100.00")
    with pytest.raises(LedgerImmutableError, match="append-only"):
        LedgerEntry.objects.bulk_update([entry], ["amount"])


@pytest.mark.django_db
def test_protect_prevents_deleting_school_or_student(school, student, term):
    """Deleting a school or student with ledger entries raises ProtectedError."""
    post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("500.00"),
    )
    with pytest.raises(ProtectedError):
        student.delete()
    with pytest.raises(ProtectedError):
        school.delete()

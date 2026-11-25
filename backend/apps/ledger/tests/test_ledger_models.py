"""Tests for LedgerEntry validation, constraints, tenant consistency, and Decimal precision."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.ledger.models import LedgerEntry


def _valid_entry(school, student, term, **overrides):
    """Build a valid unsaved LedgerEntry; callers mutate one field for negative tests."""
    defaults = {
        "school": school,
        "student": student,
        "term": term,
        "entry_type": "charge",
        "direction": "debit",
        "amount": Decimal("100.00"),
    }
    defaults.update(overrides)
    return LedgerEntry(**defaults)


@pytest.mark.django_db
def test_amount_must_be_positive_and_db_constraint_present(school, student, term):
    """Zero and negative amounts fail full_clean(); DB CheckConstraint is defined."""
    assert any(c.name == "ledger_amount_positive" for c in LedgerEntry._meta.constraints)
    entry = _valid_entry(school, student, term)
    entry.full_clean()
    for bad in (Decimal("0.00"), Decimal("-5.00")):
        entry.amount = bad
        with pytest.raises(ValidationError, match="greater than or equal to 0.01"):
            entry.full_clean()


@pytest.mark.django_db
def test_direction_rules(school, student, term):
    """Charge=debit; payment/discount/waiver=credit; adjustment allows both."""
    charge = _valid_entry(school, student, term, entry_type="charge", direction="debit")
    charge.full_clean()
    charge.direction = "credit"
    with pytest.raises(ValidationError, match="Charge entries must have direction 'debit'"):
        charge.full_clean()

    for etype in ("payment", "discount", "waiver"):
        entry = _valid_entry(school, student, term, entry_type=etype, direction="credit")
        entry.full_clean()
        entry.direction = "debit"
        with pytest.raises(ValidationError, match="must have direction 'credit'"):
            entry.full_clean()

    for direction in ("debit", "credit"):
        _valid_entry(school, student, term, entry_type="adjustment", direction=direction).full_clean()


@pytest.mark.django_db
def test_tenant_consistency_rejected(school, student, other_student, term, other_term):
    """Cross-school student or term is rejected by clean()."""
    entry = _valid_entry(school, student, term)
    entry.full_clean()
    entry.student = other_student
    with pytest.raises(ValidationError, match="Student belongs to a different school"):
        entry.full_clean()
    entry.student, entry.term = student, other_term
    with pytest.raises(ValidationError, match="Term belongs to a different school"):
        entry.full_clean()


@pytest.mark.django_db
def test_decimal_precision(school, student, term):
    """0.10 + 0.20 stored and reloaded via refresh_from_db equals Decimal('0.30')."""
    entry = LedgerEntry.objects.create(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("0.10") + Decimal("0.20"),
    )
    entry.refresh_from_db()
    assert entry.amount == Decimal("0.30")

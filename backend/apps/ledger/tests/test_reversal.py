"""Tests for reverse_entry() and database-level single-reversal enforcement."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction

from apps.ledger.models import LedgerEntry
from apps.ledger.services import post_entry, reverse_entry


@pytest.mark.django_db
def test_reverse_charge_and_payment(school, student, term, admin_user):
    """reverse_entry creates an opposite-direction entry of the same amount."""
    charge = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("1000.00"),
        created_by=admin_user,
    )
    rev_charge = reverse_entry(charge, created_by=admin_user, reason="Billed in error")
    assert rev_charge.entry_type == "reversal"
    assert rev_charge.direction == "credit"
    assert rev_charge.amount == Decimal("1000.00")
    assert rev_charge.reverses_id == charge.pk

    payment = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="payment",
        direction="credit",
        amount=Decimal("400.00"),
        created_by=admin_user,
    )
    rev_payment = reverse_entry(payment, created_by=admin_user, reason="Bounced cheque")
    assert rev_payment.direction == "debit"
    assert rev_payment.amount == Decimal("400.00")


@pytest.mark.django_db
def test_double_reversal_and_reversing_reversal_rejected(school, student, term, admin_user):
    """Second reversal and reversing a reversal both raise ValidationError."""
    charge = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("500.00"),
        created_by=admin_user,
    )
    rev = reverse_entry(charge, created_by=admin_user, reason="Valid reversal")

    with pytest.raises(ValidationError, match="already been reversed"):
        reverse_entry(charge, created_by=admin_user, reason="Duplicate")

    with pytest.raises(ValidationError, match="Cannot reverse a reversal"):
        reverse_entry(rev, created_by=admin_user, reason="Reverse reversal")


@pytest.mark.django_db
def test_empty_reason_rejected(school, student, term, admin_user):
    """Reversing without a non-empty reason raises ValidationError."""
    charge = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("200.00"),
        created_by=admin_user,
    )
    with pytest.raises(ValidationError, match="non-empty reason"):
        reverse_entry(charge, created_by=admin_user, reason="   ")


@pytest.mark.django_db
def test_db_one_to_one_blocks_second_reversal(school, student, term, admin_user):
    """The DB OneToOneField constraint rejects a hand-built second reversal."""
    charge = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("300.00"),
        created_by=admin_user,
    )
    reverse_entry(charge, created_by=admin_user, reason="First reversal")
    hand_built = LedgerEntry(
        school=school,
        student=student,
        term=term,
        entry_type="reversal",
        direction="credit",
        amount=Decimal("300.00"),
        reverses=charge,
        created_by=admin_user,
        reason="Bypass attempt",
    )
    with transaction.atomic(), pytest.raises(IntegrityError):
        models.Model.save(hand_built)

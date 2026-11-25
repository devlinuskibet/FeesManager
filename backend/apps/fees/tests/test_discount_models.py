"""Tests for Discount validation: percentage bounds, positive value, self-approval."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.fees.models import Discount


def _valid_discount(school, student, term, fee_item, admin_user, **overrides):
    """Build a valid unsaved Discount; callers mutate one field for negative tests."""
    defaults = {
        "school": school,
        "student": student,
        "term": term,
        "fee_item": fee_item,
        "kind": "percentage",
        "value": Decimal("100.00"),
        "status": "pending",
        "requested_by": admin_user,
    }
    defaults.update(overrides)
    return Discount(**defaults)


@pytest.mark.django_db
def test_percentage_bounds(school, student, term, fee_item, admin_user):
    """100% passes; 100.01% and 0% are rejected by full_clean()."""
    # Valid baseline: 100%
    disc = _valid_discount(school, student, term, fee_item, admin_user, value=Decimal("100.00"))
    disc.full_clean()

    # Mutate to > 100
    disc.value = Decimal("100.01")
    with pytest.raises(ValidationError, match="Percentage value must be between 0 and 100"):
        disc.full_clean()

    # Mutate to 0
    disc.value = Decimal("0.00")
    with pytest.raises(ValidationError, match="value must be positive"):
        disc.full_clean()


@pytest.mark.django_db
def test_fixed_positive_value(school, student, term, fee_item, admin_user):
    """Positive fixed discount passes; negative value is rejected."""
    disc = _valid_discount(school, student, term, fee_item, admin_user, kind="fixed", value=Decimal("500.00"))
    disc.full_clean()

    disc.value = Decimal("-10.00")
    with pytest.raises(ValidationError, match="value must be positive"):
        disc.full_clean()


@pytest.mark.django_db
def test_requester_cannot_approve_own_discount(school, student, term, fee_item, admin_user, bursar_user):
    """Different approver passes; requester == approver is rejected."""
    disc = _valid_discount(
        school,
        student,
        term,
        fee_item,
        admin_user,
        kind="fixed",
        value=Decimal("100.00"),
        status="approved",
        approved_by=bursar_user,
    )
    disc.full_clean()

    # Mutate approver to requester
    disc.approved_by = admin_user
    with pytest.raises(ValidationError, match="Requester cannot be the approver"):
        disc.full_clean()

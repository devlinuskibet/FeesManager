"""Tests for request_discount workflow."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.fees.discounts import request_discount
from apps.fees.models import Discount


@pytest.mark.django_db
def test_request_creates_pending_discount(school, student, term, admin_user):
    """request_discount creates a pending Discount when inputs are valid."""
    disc = request_discount(
        school=school,
        student=student,
        term=term,
        kind=Discount.Kind.FIXED,
        value=Decimal("500.00"),
        requested_by=admin_user,
        reason="Sibling discount",
    )
    assert disc.pk is not None
    assert disc.status == Discount.Status.PENDING


@pytest.mark.django_db
def test_request_empty_reason_rejected(school, student, term, admin_user):
    """An empty reason is rejected; a non-empty reason passes."""
    disc = request_discount(
        school=school,
        student=student,
        term=term,
        kind=Discount.Kind.FIXED,
        value=Decimal("500.00"),
        requested_by=admin_user,
        reason="Valid reason",
    )
    assert disc.pk is not None
    with pytest.raises(ValidationError, match="non-empty reason"):
        request_discount(
            school=school,
            student=student,
            term=term,
            kind=Discount.Kind.FIXED,
            value=Decimal("500.00"),
            requested_by=admin_user,
            reason="   ",
        )


@pytest.mark.django_db
def test_request_percentage_above_100_rejected(school, student, term, admin_user):
    """Percentage above 100 is rejected; 100 passes."""
    disc = request_discount(
        school=school,
        student=student,
        term=term,
        kind=Discount.Kind.PERCENTAGE,
        value=Decimal("100.00"),
        requested_by=admin_user,
        reason="Full bursary",
    )
    assert disc.pk is not None
    with pytest.raises(ValidationError, match="between 0 and 100"):
        request_discount(
            school=school,
            student=student,
            term=term,
            kind=Discount.Kind.PERCENTAGE,
            value=Decimal("100.01"),
            requested_by=admin_user,
            reason="Too high",
        )


@pytest.mark.django_db
def test_request_other_school_student_rejected(school, student, other_student, term, admin_user):
    """A student from another school is rejected."""
    disc = request_discount(
        school=school,
        student=student,
        term=term,
        kind=Discount.Kind.FIXED,
        value=Decimal("500.00"),
        requested_by=admin_user,
        reason="Valid student",
    )
    assert disc.pk is not None
    with pytest.raises(ValidationError, match="Student belongs to a different school"):
        request_discount(
            school=school,
            student=other_student,
            term=term,
            kind=Discount.Kind.FIXED,
            value=Decimal("500.00"),
            requested_by=admin_user,
            reason="Cross school",
        )

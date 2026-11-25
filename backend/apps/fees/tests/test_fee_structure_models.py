"""
Tests for FeeItem, FeeStructure, and FeeStructureLine uniqueness constraints.
"""

import pytest
from django.db import IntegrityError, transaction

from apps.fees.models import FeeItem, FeeStructure, FeeStructureLine


@pytest.mark.django_db
def test_fee_item_code_unique_per_school(school, other_school):
    """Same code is allowed across schools; duplicates within a school are rejected."""
    FeeItem.objects.create(school=school, code="F001", name="Tuition")
    # Same code in a different school – allowed.
    item_other = FeeItem.objects.create(school=other_school, code="F001", name="Tuition")
    assert item_other.pk is not None
    # Duplicate code in the same school – rejected.
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            FeeItem.objects.create(school=school, code="F001", name="Duplicate")


@pytest.mark.django_db
def test_fee_structure_unique_per_school_term_class(school, term, class_stream, other_school, other_term):
    """(school, term, class_stream) must be unique."""
    fs = FeeStructure.objects.create(school=school, term=term, class_stream=class_stream)
    fs.full_clean()  # valid object passes
    # Exact duplicate – rejected.
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            FeeStructure.objects.create(school=school, term=term, class_stream=class_stream)
    # Same pair but different school – allowed.
    fs2 = FeeStructure.objects.create(school=other_school, term=term, class_stream=class_stream)
    assert fs2.pk is not None
    # Different term in same school – allowed.
    fs3 = FeeStructure.objects.create(school=school, term=other_term, class_stream=class_stream)
    assert fs3.pk is not None


@pytest.mark.django_db
def test_fee_structure_line_unique_per_structure_item(school, fee_structure, fee_item, other_fee_item):
    """(fee_structure, fee_item) must be unique."""
    line = FeeStructureLine.objects.create(
        school=school,
        fee_structure=fee_structure,
        fee_item=fee_item,
        amount="5000.00",
    )
    line.full_clean()  # valid object passes
    # Duplicate – rejected.
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            FeeStructureLine.objects.create(
                school=school,
                fee_structure=fee_structure,
                fee_item=fee_item,
                amount="3000.00",
            )
    # Different fee_item in the same structure – allowed.
    line2 = FeeStructureLine.objects.create(
        school=school,
        fee_structure=fee_structure,
        fee_item=other_fee_item,
        amount="1500.00",
    )
    assert line2.pk is not None

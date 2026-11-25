"""Fixtures for fees service tests (builds on apps/fees/tests/conftest.py)."""

from decimal import Decimal

import pytest

from apps.fees.models import FeeItem, FeeStructure, FeeStructureLine
from apps.students.models import Student


@pytest.fixture
def structure_with_lines(school, fee_structure, fee_item):
    """FeeStructure with two mandatory lines (5000 + 3000) and one optional line (1500)."""
    boarding = FeeItem.objects.create(school=school, code="BD01", name="Boarding", is_optional=False)
    transport = FeeItem.objects.create(school=school, code="TR01", name="Transport", is_optional=True)
    FeeStructureLine.objects.create(
        school=school, fee_structure=fee_structure, fee_item=fee_item, amount=Decimal("5000.00")
    )
    FeeStructureLine.objects.create(
        school=school, fee_structure=fee_structure, fee_item=boarding, amount=Decimal("3000.00")
    )
    FeeStructureLine.objects.create(
        school=school, fee_structure=fee_structure, fee_item=transport, amount=Decimal("1500.00")
    )
    return fee_structure


@pytest.fixture
def second_student(school, class_stream):
    """A second active student in the same class stream."""
    return Student.objects.create(
        school=school,
        admission_number="ADM004",
        first_name="Alice",
        last_name="Wanjiku",
        class_stream=class_stream,
        status=Student.Status.ACTIVE,
        date_admitted="2024-01-15",
    )


@pytest.fixture
def inactive_student(school, class_stream):
    """An inactive (transferred) student in the default school."""
    return Student.objects.create(
        school=school,
        admission_number="ADM005",
        first_name="Bob",
        last_name="Transferred",
        class_stream=class_stream,
        status=Student.Status.TRANSFERRED,
        date_admitted="2024-01-15",
    )


@pytest.fixture
def other_school_structure(other_school, other_term, other_class_stream, other_fee_item):
    """A FeeStructure with one line in other_school."""
    fs = FeeStructure.objects.create(school=other_school, term=other_term, class_stream=other_class_stream)
    FeeStructureLine.objects.create(
        school=other_school, fee_structure=fs, fee_item=other_fee_item, amount=Decimal("7000.00")
    )
    return fs

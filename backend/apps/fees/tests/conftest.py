"""
Test fixtures for the fees app.

Reuses the ``school``, ``admin_user``, ``bursar_user`` and ``accountant_user``
fixtures defined in ``backend/conftest.py``.  Adds academic objects, students,
fee items, structures and invoices needed by the fees test suite.
"""

import pytest

from apps.academics.models import AcademicYear, ClassStream, Term
from apps.fees.models import FeeItem, FeeStructure, Invoice
from apps.students.models import Student
from apps.tenants.models import School

# -- Academic objects for the default school ----------------------------------


@pytest.fixture
def academic_year(school):
    """AcademicYear for the default school."""
    return AcademicYear.objects.create(
        school=school,
        name="2024",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )


@pytest.fixture
def term(school, academic_year):
    """Term 1 in the default school."""
    return Term.objects.create(
        school=school,
        name="term_1",
        term_number=1,
        academic_year=academic_year,
        start_date="2024-01-15",
        end_date="2024-04-05",
    )


@pytest.fixture
def class_stream(school, academic_year):
    """Form 1 East in the default school."""
    return ClassStream.objects.create(
        school=school,
        name="Form 1 East",
        level="Form 1",
        stream="East",
        academic_year=academic_year,
    )


@pytest.fixture
def student(school, class_stream):
    """A student in the default school."""
    return Student.objects.create(
        school=school,
        admission_number="ADM001",
        first_name="Jane",
        last_name="Doe",
        class_stream=class_stream,
        status="active",
        date_admitted="2024-01-15",
    )


# -- Parallel objects in a second school --------------------------------------


@pytest.fixture
def other_school(db):
    """A second school for cross-tenant tests."""
    return School.objects.create(
        name="Other School",
        slug="other-school",
        email="info@other.sc.ke",
        phone="+254700111111",
    )


@pytest.fixture
def other_academic_year(other_school):
    """AcademicYear in the other school."""
    return AcademicYear.objects.create(
        school=other_school,
        name="2024",
        start_date="2024-01-01",
        end_date="2024-12-31",
    )


@pytest.fixture
def other_term(other_school, other_academic_year):
    """Term 1 in the other school."""
    return Term.objects.create(
        school=other_school,
        name="term_1",
        term_number=1,
        academic_year=other_academic_year,
        start_date="2024-01-15",
        end_date="2024-04-05",
    )


@pytest.fixture
def other_class_stream(other_school, other_academic_year):
    """Form 1 East in the other school."""
    return ClassStream.objects.create(
        school=other_school,
        name="Form 1 East",
        level="Form 1",
        stream="East",
        academic_year=other_academic_year,
    )


@pytest.fixture
def other_student(other_school, other_class_stream):
    """A student in the other school."""
    return Student.objects.create(
        school=other_school,
        admission_number="ADM002",
        first_name="Other",
        last_name="Student",
        class_stream=other_class_stream,
        status="active",
        date_admitted="2024-01-15",
    )


@pytest.fixture
def fee_item(school):
    """A fee item in the default school."""
    return FeeItem.objects.create(
        school=school,
        code="TU01",
        name="Tuition",
    )


@pytest.fixture
def other_fee_item(other_school):
    """A fee item in the other school."""
    return FeeItem.objects.create(
        school=other_school,
        code="TU01",
        name="Tuition",
    )


@pytest.fixture
def fee_structure(school, term, class_stream):
    """FeeStructure in the default school."""
    return FeeStructure.objects.create(
        school=school,
        term=term,
        class_stream=class_stream,
    )


@pytest.fixture
def invoice(school, student, term, admin_user):
    """A draft invoice in the default school."""
    return Invoice.objects.create(
        school=school,
        student=student,
        term=term,
        invoice_number="INV-2024-00001",
        invoice_year=2024,
        sequence=1,
        invoice_type="term",
        status="draft",
        created_by=admin_user,
    )

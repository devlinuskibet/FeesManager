"""Test fixtures for the ledger app.

Reuses ``school``, ``admin_user``, and ``bursar_user`` from ``backend/conftest.py``.
"""

import pytest

from apps.academics.models import AcademicYear, ClassStream, Term
from apps.students.models import Student
from apps.tenants.models import School


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
def term_2(school, academic_year):
    """Term 2 in the default school for multi-term balance tests."""
    return Term.objects.create(
        school=school,
        name="term_2",
        term_number=2,
        academic_year=academic_year,
        start_date="2024-05-06",
        end_date="2024-08-02",
    )


@pytest.fixture
def class_stream(school, academic_year):
    """ClassStream in the default school."""
    return ClassStream.objects.create(
        school=school,
        name="Form 1 East",
        level="Form 1",
        stream="East",
        academic_year=academic_year,
    )


@pytest.fixture
def student(school, class_stream):
    """Primary student in the default school."""
    return Student.objects.create(
        school=school,
        admission_number="ADM001",
        first_name="Jane",
        last_name="Doe",
        class_stream=class_stream,
        status="active",
        date_admitted="2024-01-15",
    )


@pytest.fixture
def other_student_same_school(school, class_stream):
    """Second student in the same school to verify per-student isolation."""
    return Student.objects.create(
        school=school,
        admission_number="ADM003",
        first_name="John",
        last_name="Smith",
        class_stream=class_stream,
        status="active",
        date_admitted="2024-01-15",
    )


@pytest.fixture
def other_school(db):
    """Second school for cross-tenant tests."""
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
    """ClassStream in the other school."""
    return ClassStream.objects.create(
        school=other_school,
        name="Form 1 East",
        level="Form 1",
        stream="East",
        academic_year=other_academic_year,
    )


@pytest.fixture
def other_student(other_school, other_class_stream):
    """Student in the other school."""
    return Student.objects.create(
        school=other_school,
        admission_number="ADM002",
        first_name="Other",
        last_name="Student",
        class_stream=other_class_stream,
        status="active",
        date_admitted="2024-01-15",
    )

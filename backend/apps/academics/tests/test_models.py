"""Tests for AcademicYear, Term, and ClassStream models."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from ..models import AcademicYear, ClassStream, Term


@pytest.mark.django_db
def test_academic_year_creation_and_str(school):
    ay = AcademicYear.objects.create(
        school=school,
        name="2027",
        start_date="2027-01-01",
        end_date="2027-12-31",
        is_current=True,
    )
    assert ay.pk is not None
    assert str(ay) == "2027 (demo-school)"
    assert ay.school == school


@pytest.mark.django_db
def test_academic_year_name_unique_per_school(school):
    AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    with pytest.raises(IntegrityError):
        AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")


@pytest.mark.django_db
def test_only_one_current_academic_year_per_school(school):
    AcademicYear.objects.create(
        school=school,
        name="2026",
        start_date="2026-01-01",
        end_date="2026-12-31",
        is_current=True,
    )
    # create() bypasses clean(); use full_clean() to exercise the
    # "one current year per school" application-level rule.
    dup = AcademicYear(
        school=school,
        name="2027",
        start_date="2027-01-01",
        end_date="2027-12-31",
        is_current=True,
    )
    with pytest.raises(ValidationError):
        dup.full_clean()


@pytest.mark.django_db
def test_term_creation_and_str(school):
    ay = AcademicYear.objects.create(
        school=school,
        name="2027",
        start_date="2027-01-01",
        end_date="2027-12-31",
    )
    term = Term.objects.create(
        school=school,
        academic_year=ay,
        name="term_1",
        term_number=1,
        start_date="2027-01-05",
        end_date="2027-04-05",
        is_active=True,
    )
    assert term.pk is not None
    assert "Term 1" in str(term)


@pytest.mark.django_db
def test_class_stream_auto_name(school):
    ay = AcademicYear.objects.create(
        school=school,
        name="2027",
        start_date="2027-01-01",
        end_date="2027-12-31",
    )
    cs = ClassStream.objects.create(
        school=school,
        level="Form 1",
        stream="East",
        academic_year=ay,
    )
    assert cs.name == "Form 1 East"
    assert str(cs) == "Form 1 East"


@pytest.mark.django_db
def test_class_stream_unique_per_school_and_year(school):
    ay = AcademicYear.objects.create(
        school=school,
        name="2027",
        start_date="2027-01-01",
        end_date="2027-12-31",
    )
    ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)
    with pytest.raises(IntegrityError):
        ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)

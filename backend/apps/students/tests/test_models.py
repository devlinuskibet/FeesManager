"""Tests for Student, Guardian, StudentGuardian models."""

import pytest
from django.db import IntegrityError

from apps.academics.models import AcademicYear, ClassStream
from apps.students.models import Guardian, Student, StudentGuardian


@pytest.mark.django_db
def test_student_admission_number_normalized(school):
    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    cs = ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)
    s = Student.objects.create(
        school=school,
        admission_number=" adm 001 ",
        first_name="John",
        last_name="Doe",
        class_stream=cs,
        date_admitted="2027-01-10",
    )
    assert s.admission_number == "ADM001"
    assert s.full_name == "John Doe"


@pytest.mark.django_db
def test_student_admission_unique_per_school(school):
    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    cs = ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)
    Student.objects.create(
        school=school,
        admission_number="ADM001",
        first_name="John",
        last_name="Doe",
        class_stream=cs,
        date_admitted="2027-01-10",
    )
    with pytest.raises(IntegrityError):
        Student.objects.create(
            school=school,
            admission_number="ADM001",
            first_name="Jane",
            last_name="Doe",
            class_stream=cs,
            date_admitted="2027-01-10",
        )


@pytest.mark.django_db
def test_guardian_e164_phone(school):
    g = Guardian.objects.create(
        school=school,
        name="Jane Doe",
        phone="+254712345678",
        relationship="mother",
        is_primary=True,
    )
    assert g.pk is not None
    assert g.phone == "+254712345678"


@pytest.mark.django_db
def test_student_guardian_link(school):
    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    cs = ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)
    s = Student.objects.create(
        school=school,
        admission_number="ADM001",
        first_name="John",
        last_name="Doe",
        class_stream=cs,
        date_admitted="2027-01-10",
    )
    g = Guardian.objects.create(school=school, name="Jane Doe", phone="+254712345678", relationship="mother")
    link = StudentGuardian.objects.create(school=school, student=s, guardian=g, is_primary=True)
    assert link.pk is not None
    assert s.guardian_links.count() == 1
    assert g.student_links.count() == 1

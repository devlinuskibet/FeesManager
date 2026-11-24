"""Tests for the bulk import service (dry-run, validation, atomic commit)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.academics.models import AcademicYear, ClassStream
from apps.students.import_service import import_students
from apps.students.models import Guardian, Student, StudentGuardian


def _make_csv(school, rows_text):
    """Build a CSV file content with a header row."""
    header = (
        "student_admission_number,student_first_name,student_last_name,"
        "class_stream_level,class_stream_stream,student_status,student_date_admitted,"
        "guardian_name,guardian_phone,guardian_relationship,guardian_is_primary\n"
    )
    content = header + rows_text
    return SimpleUploadedFile("students.csv", content.encode("utf-8"))


@pytest.mark.django_db
def test_import_dry_run_creates_nothing(school, admin_user):
    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)

    csv_file = _make_csv(
        school,
        "ADM001,John,Doe,Form 1,East,active,2027-01-10,Jane Doe,+254712345678,mother,true\n",
    )

    report = import_students(csv_file, school, dry_run=True, user=admin_user)

    assert report["dry_run"] is True
    assert report["total_rows"] == 1
    assert report["valid_rows"] == 1
    assert report["invalid_rows"] == 0
    assert report["status"] == "ok"
    # Nothing persisted
    assert Student.objects.for_school(school).count() == 0
    assert Guardian.objects.for_school(school).count() == 0


@pytest.mark.django_db
def test_import_commit_creates_records(school, admin_user):
    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)

    csv_file = _make_csv(
        school,
        "ADM001,John,Doe,Form 1,East,active,2027-01-10,Jane Doe,+254712345678,mother,true\n",
    )

    report = import_students(csv_file, school, dry_run=False, user=admin_user)

    assert report["status"] == "ok"
    assert report["created_students"] == 1
    assert report["created_guardians"] == 1
    assert report["created_links"] == 1

    s = Student.objects.for_school(school).get(admission_number="ADM001")
    assert s.first_name == "John"
    assert s.last_name == "Doe"
    assert s.status == "active"

    g = Guardian.objects.for_school(school).get(phone="+254712345678")
    assert g.name == "Jane Doe"

    assert StudentGuardian.objects.for_school(school).count() == 1


@pytest.mark.django_db
def test_import_detects_duplicate_within_file(school):
    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)

    csv_file = _make_csv(
        school,
        "ADM001,John,Doe,Form 1,East,active,2027-01-10,Jane Doe,+254712345678,mother,true\n"
        "ADM001,Jane,Doe,Form 1,East,active,2027-01-10,John Doe,+254712345679,father,true\n",
    )

    report = import_students(csv_file, school, dry_run=True, user=None)

    assert report["status"] == "has_errors"
    assert report["invalid_rows"] == 1  # second row is a dup
    assert report["valid_rows"] == 1
    assert "ADM001" in report["duplicate_admission_numbers"]
    # Row 3 (the duplicate) has an error
    dup_row = [r for r in report["rows"] if r["row_number"] == 3][0]
    assert "Duplicate admission number" in dup_row["errors"][0]


@pytest.mark.django_db
def test_import_rejects_bad_phone(school):
    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)

    csv_file = _make_csv(
        school,
        "ADM001,John,Doe,Form 1,East,active,2027-01-10,Jane Doe,not-a-phone,mother,true\n",
    )

    report = import_students(csv_file, school, dry_run=True, user=None)

    assert report["status"] == "has_errors"
    assert report["invalid_rows"] == 1
    # With a single data row, it occupies report["rows"][0]
    assert any("guardian_phone" in e for e in report["rows"][0]["errors"])


@pytest.mark.django_db
def test_import_missing_class_stream_reported(school):
    AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    # No ClassStream created

    csv_file = _make_csv(
        school,
        "ADM001,John,Doe,Form 99,East,active,2027-01-10,Jane Doe,+254712345678,mother,true\n",
    )

    report = import_students(csv_file, school, dry_run=True, user=None)

    assert report["status"] == "has_errors"
    assert report["invalid_rows"] == 1
    # With a single data row, it occupies report["rows"][0]
    assert any("not found" in e for e in report["rows"][0]["errors"])

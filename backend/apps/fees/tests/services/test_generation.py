"""Tests for idempotent term invoice generation."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import ClassStream
from apps.fees.generation import generate_term_invoices
from apps.fees.issuing import invoice_total
from apps.fees.models import Invoice, InvoiceLine, InvoiceSequence
from apps.students.models import Student


@pytest.mark.django_db
def test_creates_one_invoice_per_active_student_with_lines_and_totals(
    school, term, student, second_student, structure_with_lines, admin_user
):
    """Each active student gets one draft term invoice with matching lines and total."""
    res = generate_term_invoices(school=school, term=term, created_by=admin_user)
    assert (res.created, res.skipped_existing, res.skipped_no_structure) == (2, 0, 0)
    assert Invoice.objects.for_school(school).count() == 2
    for stu in (student, second_student):
        inv = Invoice.objects.get(school=school, student=stu, term=term, invoice_type="term")
        assert inv.status == Invoice.Status.DRAFT
        assert invoice_total(inv) == Decimal("8000.00")


@pytest.mark.django_db
def test_optional_fee_items_excluded(school, term, student, structure_with_lines):
    """Optional fee items are excluded from generated term invoices."""
    generate_term_invoices(school=school, term=term)
    inv = Invoice.objects.get(school=school, student=student, term=term, invoice_type="term")
    assert inv.lines.count() == 2
    assert not inv.lines.filter(fee_item__is_optional=True).exists()


@pytest.mark.django_db
def test_inactive_student_skipped(school, term, student, inactive_student, structure_with_lines):
    """Inactive students do not receive generated term invoices."""
    assert generate_term_invoices(school=school, term=term).created == 1
    assert not Invoice.objects.filter(student=inactive_student).exists()


@pytest.mark.django_db
def test_student_without_structure_skipped(school, academic_year, term, student, structure_with_lines):
    """A student whose class stream lacks a FeeStructure counts as skipped_no_structure."""
    cs = ClassStream.objects.create(
        school=school, name="Form 2 West", level="Form 2", stream="West", academic_year=academic_year
    )
    Student.objects.create(
        school=school,
        admission_number="ADM099",
        first_name="No",
        last_name="Struct",
        class_stream=cs,
        status=Student.Status.ACTIVE,
        date_admitted="2024-01-15",
    )
    res = generate_term_invoices(school=school, term=term)
    assert (res.created, res.skipped_no_structure) == (1, 1)


@pytest.mark.django_db
def test_idempotent_second_run_creates_nothing(school, term, student, structure_with_lines):
    """Running generation twice creates nothing on the second run."""
    assert generate_term_invoices(school=school, term=term).created == 1
    second = generate_term_invoices(school=school, term=term)
    assert (second.created, second.skipped_existing) == (0, 1)
    assert Invoice.objects.count() == 1


@pytest.mark.django_db
def test_dry_run_writes_nothing_and_returns_previews(school, term, student, structure_with_lines):
    """dry_run=True writes no invoices, lines, or sequences and populates previews."""
    res = generate_term_invoices(school=school, term=term, dry_run=True)
    assert Invoice.objects.count() == InvoiceLine.objects.count() == InvoiceSequence.objects.count() == 0
    assert len(res.previews) == 1
    assert res.previews[0]["admission_number"] == student.admission_number
    assert res.previews[0]["total"] == Decimal("8000.00")


@pytest.mark.django_db
def test_other_school_students_and_structure_untouched(
    school, term, student, structure_with_lines, other_school, other_student, other_school_structure
):
    """Generating for one school never touches another school's students or structures."""
    generate_term_invoices(school=school, term=term)
    assert Invoice.objects.for_school(other_school).count() == 0


@pytest.mark.django_db
def test_term_from_other_school_rejected(school, term, other_term, student, structure_with_lines):
    """Passing a term belonging to another school raises ValidationError."""
    assert generate_term_invoices(school=school, term=term).created == 1
    with pytest.raises(ValidationError, match="Term does not belong to the specified school"):
        generate_term_invoices(school=school, term=other_term)

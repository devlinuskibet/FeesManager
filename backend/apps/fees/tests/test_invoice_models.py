"""Tests for Invoice constraints, InvoiceLine nullability, and Decimal precision."""

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.fees.models import Invoice, InvoiceLine


@pytest.mark.django_db
def test_invoice_unique_school_student_term_type(school, student, term, admin_user):
    """(school, student, term, invoice_type) must be unique."""
    inv = Invoice.objects.create(
        school=school,
        student=student,
        term=term,
        invoice_number="INV-2024-00010",
        invoice_year=2024,
        sequence=10,
        invoice_type="term",
        created_by=admin_user,
    )
    inv.full_clean()
    with transaction.atomic(), pytest.raises(IntegrityError):
        Invoice.objects.create(
            school=school,
            student=student,
            term=term,
            invoice_number="INV-2024-00011",
            invoice_year=2024,
            sequence=11,
            invoice_type="term",
            created_by=admin_user,
        )


@pytest.mark.django_db
def test_invoice_number_unique_per_school(school, student, term, admin_user, other_school, other_student, other_term):
    """Same invoice_number is allowed across schools but rejected within one school."""
    Invoice.objects.create(
        school=school,
        student=student,
        term=term,
        invoice_number="INV-2024-00020",
        invoice_year=2024,
        sequence=20,
        invoice_type="term",
        created_by=admin_user,
    )
    inv_other = Invoice.objects.create(
        school=other_school,
        student=other_student,
        term=other_term,
        invoice_number="INV-2024-00020",
        invoice_year=2024,
        sequence=20,
        invoice_type="term",
        created_by=admin_user,
    )
    assert inv_other.pk is not None
    with transaction.atomic(), pytest.raises(IntegrityError):
        Invoice.objects.create(
            school=school,
            student=student,
            term=term,
            invoice_number="INV-2024-00020",
            invoice_year=2024,
            sequence=21,
            invoice_type="adhoc",
            created_by=admin_user,
        )


@pytest.mark.django_db
def test_invoice_year_sequence_unique_per_school(school, student, term, admin_user):
    """(school, invoice_year, sequence) must be unique per school."""
    Invoice.objects.create(
        school=school,
        student=student,
        term=term,
        invoice_number="INV-2024-00030",
        invoice_year=2024,
        sequence=30,
        invoice_type="term",
        created_by=admin_user,
    )
    with transaction.atomic(), pytest.raises(IntegrityError):
        Invoice.objects.create(
            school=school,
            student=student,
            term=term,
            invoice_number="INV-2024-00031",
            invoice_year=2024,
            sequence=30,
            invoice_type="adhoc",
            created_by=admin_user,
        )


@pytest.mark.django_db
def test_invoice_line_null_fee_item(school, invoice):
    """InvoiceLine with fee_item=None (ad-hoc charge) passes full_clean()."""
    line = InvoiceLine(school=school, invoice=invoice, fee_item=None, description="Ad-hoc charge", amount="300.00")
    line.full_clean()


@pytest.mark.django_db
def test_decimal_precision(school, invoice):
    """Decimal("0.10") + Decimal("0.20") is stored and read back as Decimal("0.30")."""
    line = InvoiceLine.objects.create(
        school=school,
        invoice=invoice,
        fee_item=None,
        description="Precision test",
        amount=Decimal("0.10") + Decimal("0.20"),
    )
    line.refresh_from_db()
    assert line.amount == Decimal("0.30")

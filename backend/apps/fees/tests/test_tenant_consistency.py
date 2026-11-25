"""Tenant-consistency tests: clean() rejects cross-school links; school is non-nullable."""

import pytest
from django.core.exceptions import ValidationError

from apps.fees.models import Discount, FeeItem, FeeStructure, FeeStructureLine, Invoice, InvoiceLine


@pytest.mark.django_db
def test_invoice_cross_school_rejected(school, student, other_student, term, other_term, admin_user):
    """Invoice.clean() rejects a student or term from another school."""
    inv = Invoice(
        school=school,
        student=student,
        term=term,
        invoice_number="INV-2024-09001",
        invoice_year=2024,
        sequence=9001,
        invoice_type="term",
        status="draft",
        created_by=admin_user,
    )
    inv.full_clean()
    inv.student = other_student
    with pytest.raises(ValidationError, match="Student belongs to a different school"):
        inv.full_clean()
    inv.student, inv.term = student, other_term
    with pytest.raises(ValidationError, match="Term belongs to a different school"):
        inv.full_clean()


@pytest.mark.django_db
def test_invoice_line_cross_school_rejected(school, invoice, fee_item, other_fee_item):
    """InvoiceLine.clean() rejects a fee item from another school."""
    line = InvoiceLine(school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount="100.00")
    line.full_clean()
    line.fee_item = other_fee_item
    with pytest.raises(ValidationError, match="FeeItem belongs to a different school"):
        line.full_clean()


@pytest.mark.django_db
def test_fee_structure_and_line_cross_school_rejected(
    school,
    term,
    other_term,
    class_stream,
    other_class_stream,
    fee_structure,
    fee_item,
    other_fee_item,
):
    """FeeStructure and FeeStructureLine reject cross-school relations."""
    fee_structure.full_clean()
    fee_structure.term = other_term
    with pytest.raises(ValidationError, match="Term belongs to a different school"):
        fee_structure.full_clean()
    fee_structure.term, fee_structure.class_stream = term, other_class_stream
    with pytest.raises(ValidationError, match="Class stream belongs to a different school"):
        fee_structure.full_clean()
    fee_structure.class_stream = class_stream

    line = FeeStructureLine(school=school, fee_structure=fee_structure, fee_item=fee_item, amount="200.00")
    line.full_clean()
    line.fee_item = other_fee_item
    with pytest.raises(ValidationError, match="fee item belong to different schools"):
        line.full_clean()


@pytest.mark.django_db
def test_discount_cross_school_rejected(school, student, other_student, term, fee_item, other_fee_item, admin_user):
    """Discount.clean() rejects a student or fee item from another school."""
    disc = Discount(
        school=school,
        student=student,
        term=term,
        fee_item=fee_item,
        kind="fixed",
        value="100.00",
        status="pending",
        requested_by=admin_user,
    )
    disc.full_clean()
    disc.student = other_student
    with pytest.raises(ValidationError, match="Student belongs to a different school"):
        disc.full_clean()
    disc.student, disc.fee_item = student, other_fee_item
    with pytest.raises(ValidationError, match="FeeItem belongs to a different school"):
        disc.full_clean()


@pytest.mark.parametrize("model_cls", [FeeItem, FeeStructure, FeeStructureLine, Invoice, InvoiceLine, Discount])
def test_school_non_nullable(model_cls):
    """Every fees model has a required (non-nullable) school FK."""
    assert not model_cls._meta.get_field("school").null

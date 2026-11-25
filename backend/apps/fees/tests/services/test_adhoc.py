"""Tests for add_invoice_line and add_adhoc_charge."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.fees.adhoc import add_adhoc_charge, add_invoice_line
from apps.fees.issuing import cancel_invoice, issue_invoice
from apps.fees.models import Invoice, InvoiceLine
from apps.ledger.balances import student_balance


@pytest.mark.django_db
def test_add_adhoc_charge_creates_draft_invoice_with_line(school, student, term, admin_user):
    """add_adhoc_charge creates a numbered draft adhoc invoice with one line."""
    line = add_adhoc_charge(
        school=school,
        student=student,
        term=term,
        description="Broken window",
        amount=Decimal("750.00"),
        created_by=admin_user,
    )
    assert line.invoice.invoice_type == Invoice.InvoiceType.ADHOC
    assert line.invoice.status == Invoice.Status.DRAFT
    assert line.invoice.invoice_number.startswith(f"INV-{str(term.start_date)[:4]}-")
    assert line.invoice.lines.count() == 1


@pytest.mark.django_db
def test_second_adhoc_charge_reuses_same_invoice(school, student, term, admin_user):
    """A second adhoc charge for the same (school, student, term) reuses the same invoice."""
    line1 = add_adhoc_charge(
        school=school,
        student=student,
        term=term,
        description="Damaged desk",
        amount=Decimal("500.00"),
        created_by=admin_user,
    )
    line2 = add_adhoc_charge(
        school=school,
        student=student,
        term=term,
        description="Lost book",
        amount=Decimal("300.00"),
        created_by=admin_user,
    )
    assert line1.invoice_id == line2.invoice_id
    assert Invoice.objects.filter(school=school, student=student, term=term, invoice_type="adhoc").count() == 1


@pytest.mark.django_db
def test_add_line_to_issued_invoice_posts_charge_immediately(school, invoice, fee_item, student, admin_user):
    """Adding a line to an issued invoice posts a ledger charge and raises student_balance."""
    InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("5000.00")
    )
    issue_invoice(invoice, issued_by=admin_user)
    assert student_balance(student) == Decimal("5000.00")

    add_invoice_line(invoice, description="Late fee", amount=Decimal("250.00"), added_by=admin_user)
    assert student_balance(student) == Decimal("5250.00")


@pytest.mark.django_db
def test_add_line_to_cancelled_invoice_rejected(school, invoice, admin_user):
    """Adding a line to a cancelled invoice raises ValidationError."""
    add_invoice_line(invoice, description="Valid draft line", amount=Decimal("100.00"))
    cancel_invoice(invoice, cancelled_by=admin_user, reason="Cancelled")
    with pytest.raises(ValidationError, match="cancelled invoice"):
        add_invoice_line(invoice, description="Blocked", amount=Decimal("100.00"))


@pytest.mark.django_db
def test_add_line_negative_amount_rejected(school, invoice):
    """A negative line amount raises ValidationError."""
    add_invoice_line(invoice, description="Positive", amount=Decimal("100.00"))
    with pytest.raises(ValidationError, match="greater than zero"):
        add_invoice_line(invoice, description="Negative", amount=Decimal("-50.00"))


@pytest.mark.django_db
def test_add_line_school_matches_invoice_school(school, student, term, admin_user):
    """The created InvoiceLine inherits the invoice's school."""
    line = add_adhoc_charge(
        school=school,
        student=student,
        term=term,
        description="Uniform",
        amount=Decimal("1200.00"),
        created_by=admin_user,
    )
    assert line.school_id == line.invoice.school_id == school.id

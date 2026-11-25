"""Tests for invoice_total and issue_invoice wired to the ledger."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.fees.issuing import cancel_invoice, invoice_total, issue_invoice
from apps.fees.models import Invoice, InvoiceLine
from apps.ledger.balances import student_balance
from apps.ledger.models import LedgerEntry


@pytest.mark.django_db
def test_issue_creates_debit_charges_and_updates_balance(school, invoice, fee_item, student, admin_user):
    """Issuing creates one debit charge per line and student_balance equals invoice_total."""
    line1 = InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("5000.00")
    )
    line2 = InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=None, description="Lab", amount=Decimal("1200.00")
    )
    issue_invoice(invoice, issued_by=admin_user)

    entries = LedgerEntry.objects.for_school(school).filter(student=student)
    assert entries.count() == 2
    assert {(e.source_type, e.source_id, e.reference, e.direction) for e in entries} == {
        ("invoice_line", line1.id, invoice.invoice_number, "debit"),
        ("invoice_line", line2.id, invoice.invoice_number, "debit"),
    }
    assert student_balance(student) == invoice_total(invoice) == Decimal("6200.00")


@pytest.mark.django_db
def test_issue_sets_status_and_issued_at(school, invoice, fee_item, admin_user):
    """issue_invoice sets status='issued' and populates issued_at."""
    InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("1000.00")
    )
    issued = issue_invoice(invoice, issued_by=admin_user)
    assert issued.status == Invoice.Status.ISSUED
    assert issued.issued_at is not None


@pytest.mark.django_db
def test_issue_twice_raises_and_posts_nothing(school, invoice, fee_item, admin_user):
    """Issuing an already issued invoice raises ValidationError and posts nothing."""
    InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("1000.00")
    )
    issue_invoice(invoice, issued_by=admin_user)
    before = LedgerEntry.objects.count()
    with pytest.raises(ValidationError, match="Only draft invoices can be issued"):
        issue_invoice(invoice, issued_by=admin_user)
    assert LedgerEntry.objects.count() == before


@pytest.mark.django_db
def test_issue_empty_invoice_rejected(school, invoice, admin_user):
    """An invoice with no lines is rejected; adding a valid line makes it pass."""
    with pytest.raises(ValidationError, match="no lines"):
        issue_invoice(invoice, issued_by=admin_user)
    InvoiceLine.objects.create(school=school, invoice=invoice, description="Tuition", amount=Decimal("500.00"))
    assert issue_invoice(invoice, issued_by=admin_user).status == Invoice.Status.ISSUED


@pytest.mark.django_db
def test_issue_zero_amount_line_rolls_back(school, invoice, fee_item, admin_user):
    """A zero-amount line rejects issuance and rolls back status and ledger writes."""
    InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Valid", amount=Decimal("1000.00")
    )
    bad_line = InvoiceLine.objects.create(school=school, invoice=invoice, description="Zero", amount=Decimal("0.00"))
    with pytest.raises(ValidationError, match="greater than zero"):
        issue_invoice(invoice, issued_by=admin_user)
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.DRAFT
    assert LedgerEntry.objects.count() == 0
    bad_line.delete()
    assert issue_invoice(invoice, issued_by=admin_user).status == Invoice.Status.ISSUED


@pytest.mark.django_db
def test_issue_cancelled_invoice_rejected(school, invoice, fee_item, admin_user):
    """Issuing a cancelled invoice raises ValidationError."""
    InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("1000.00")
    )
    cancel_invoice(invoice, cancelled_by=admin_user, reason="Not needed")
    with pytest.raises(ValidationError, match="Only draft invoices can be issued"):
        issue_invoice(invoice, issued_by=admin_user)


@pytest.mark.django_db
def test_invoice_total_decimal_exact(school, invoice):
    """invoice_total sums 0.10 + 0.20 to exact Decimal('0.30')."""
    InvoiceLine.objects.create(school=school, invoice=invoice, description="A", amount=Decimal("0.10"))
    InvoiceLine.objects.create(school=school, invoice=invoice, description="B", amount=Decimal("0.20"))
    assert invoice_total(invoice) == Decimal("0.30")

"""Tests for cancel_invoice wired to ledger reversals and audit hook."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.fees import issuing
from apps.fees.issuing import cancel_invoice, issue_invoice
from apps.fees.models import Invoice, InvoiceLine
from apps.ledger.balances import student_balance
from apps.ledger.models import LedgerEntry
from apps.ledger.services import reverse_entry


@pytest.mark.django_db
def test_cancel_draft_creates_no_ledger_entries(school, invoice, admin_user):
    """Cancelling a draft invoice sets status='cancelled' with no ledger writes."""
    cancelled = cancel_invoice(invoice, cancelled_by=admin_user, reason="Draft error")
    assert cancelled.status == Invoice.Status.CANCELLED
    assert LedgerEntry.objects.count() == 0


@pytest.mark.django_db
def test_cancel_issued_reverses_all_charges_and_zeroes_balance(school, invoice, fee_item, student, admin_user):
    """Cancelling an issued invoice reverses every charge and brings balance to 0.00."""
    InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("5000.00")
    )
    InvoiceLine.objects.create(school=school, invoice=invoice, description="Lab", amount=Decimal("1000.00"))
    issue_invoice(invoice, issued_by=admin_user)
    assert student_balance(student) == Decimal("6000.00")

    cancelled = cancel_invoice(invoice, cancelled_by=admin_user, reason="Withdrawn")
    assert cancelled.status == Invoice.Status.CANCELLED
    assert student_balance(student) == Decimal("0.00")


@pytest.mark.django_db
def test_cancel_preserves_original_charge_entries(school, invoice, fee_item, admin_user):
    """Original charge entries remain in the append-only ledger after cancellation."""
    InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("2500.00")
    )
    issue_invoice(invoice, issued_by=admin_user)
    cancel_invoice(invoice, cancelled_by=admin_user, reason="Duplicate")
    assert LedgerEntry.objects.filter(entry_type="charge").count() == 1
    assert LedgerEntry.objects.filter(entry_type="reversal").count() == 1


@pytest.mark.django_db
def test_cancel_twice_raises(school, invoice, admin_user):
    """Cancelling an already cancelled invoice raises ValidationError."""
    cancel_invoice(invoice, cancelled_by=admin_user, reason="First cancel")
    with pytest.raises(ValidationError, match="already cancelled"):
        cancel_invoice(invoice, cancelled_by=admin_user, reason="Second cancel")


@pytest.mark.django_db
def test_cancel_empty_reason_raises(school, invoice, admin_user):
    """Cancelling without a non-empty reason raises ValidationError."""
    with pytest.raises(ValidationError, match="non-empty reason"):
        cancel_invoice(invoice, cancelled_by=admin_user, reason="   ")
    assert cancel_invoice(invoice, cancelled_by=admin_user, reason="Valid").status == Invoice.Status.CANCELLED


@pytest.mark.django_db
def test_cancel_with_partly_reversed_lines_succeeds(school, invoice, fee_item, student, admin_user):
    """Cancelling an issued invoice whose lines were partly reversed skips already-reversed entries."""
    line1 = InvoiceLine.objects.create(
        school=school, invoice=invoice, fee_item=fee_item, description="Tuition", amount=Decimal("4000.00")
    )
    InvoiceLine.objects.create(school=school, invoice=invoice, description="Exam", amount=Decimal("1000.00"))
    issue_invoice(invoice, issued_by=admin_user)
    charge1 = LedgerEntry.objects.get(source_type="invoice_line", source_id=line1.id)
    reverse_entry(charge1, created_by=admin_user, reason="Partial adjustment")

    cancel_invoice(invoice, cancelled_by=admin_user, reason="Full cancel")
    assert student_balance(student) == Decimal("0.00")
    assert LedgerEntry.objects.filter(entry_type="reversal").count() == 2


@pytest.mark.django_db
def test_cancel_calls_record_audit_event(monkeypatch, school, invoice, admin_user):
    """cancel_invoice calls record_audit_event with 'invoice.cancelled'."""
    calls = []
    monkeypatch.setattr(issuing, "record_audit_event", lambda action, **kw: calls.append((action, kw)))
    cancel_invoice(invoice, cancelled_by=admin_user, reason="Audit check")
    assert len(calls) == 1
    assert calls[0][0] == "invoice.cancelled"
    assert calls[0][1]["actor"] == admin_user
    assert calls[0][1]["obj"].pk == invoice.pk

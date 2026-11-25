"""Tests for approve_discount, reject_discount, and discount_amount (13 cases)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.fees import discounts
from apps.fees.discounts import approve_discount, reject_discount, request_discount
from apps.fees.issuing import cancel_invoice, issue_invoice
from apps.fees.models import Discount, Invoice, InvoiceLine
from apps.ledger.balances import student_balance
from apps.ledger.models import LedgerEntry


def _req(school, student, term, admin_user, kind="fixed", value="1000.00", fee_item=None):
    return request_discount(
        school=school,
        student=student,
        term=term,
        fee_item=fee_item,
        kind=kind,
        value=Decimal(value),
        requested_by=admin_user,
        reason="Approved aid",
    )


@pytest.mark.django_db
def test_fixed_approval_posts_credit_and_lowers_balance(school, student, term, issued_invoice, admin_user, bursar_user):
    disc = approve_discount(_req(school, student, term, admin_user, "fixed", "1500.00"), approved_by=bursar_user)
    entry = LedgerEntry.objects.get(source_type="discount", source_id=disc.id)
    assert (entry.entry_type, entry.direction, entry.amount, entry.reference) == (
        "discount",
        "credit",
        Decimal("1500.00"),
        f"Discount {disc.id}",
    )
    assert student_balance(student) == Decimal("8500.00")


@pytest.mark.django_db
def test_percentage_10_of_10000_posts_1000(school, student, term, issued_invoice, admin_user, bursar_user):
    disc = approve_discount(_req(school, student, term, admin_user, "percentage", "10.00"), approved_by=bursar_user)
    assert LedgerEntry.objects.get(source_type="discount", source_id=disc.id).amount == Decimal("1000.00")


@pytest.mark.django_db
def test_percentage_scoped_to_fee_item(school, student, term, issued_invoice, fee_item, admin_user, bursar_user):
    disc = approve_discount(
        _req(school, student, term, admin_user, "percentage", "10.00", fee_item), approved_by=bursar_user
    )
    assert LedgerEntry.objects.get(source_type="discount", source_id=disc.id).amount == Decimal("600.00")


@pytest.mark.django_db
def test_percentage_rounding_half_up(school, second_student, term, admin_user, bursar_user):
    inv = Invoice.objects.create(
        school=school,
        student=second_student,
        term=term,
        invoice_number="INV-2024-00201",
        invoice_year=2024,
        sequence=201,
        invoice_type="term",
        created_by=admin_user,
    )
    InvoiceLine.objects.create(school=school, invoice=inv, description="Misc", amount=Decimal("10.10"))
    issue_invoice(inv, issued_by=admin_user)
    disc = approve_discount(
        _req(school, second_student, term, admin_user, "percentage", "5.00"), approved_by=bursar_user
    )
    assert LedgerEntry.objects.get(source_type="discount", source_id=disc.id).amount == Decimal("0.51")


@pytest.mark.django_db
def test_requester_cannot_approve_own_discount(school, student, term, issued_invoice, admin_user, bursar_user):
    disc = _req(school, student, term, admin_user, "fixed", "500.00")
    before = LedgerEntry.objects.count()
    with pytest.raises(ValidationError, match="Requester cannot be the approver"):
        approve_discount(disc, approved_by=admin_user)
    assert LedgerEntry.objects.count() == before
    assert approve_discount(disc, approved_by=bursar_user).status == Discount.Status.APPROVED


@pytest.mark.django_db
def test_approving_twice_raises(school, student, term, issued_invoice, admin_user, bursar_user):
    disc = approve_discount(_req(school, student, term, admin_user), approved_by=bursar_user)
    before = LedgerEntry.objects.count()
    with pytest.raises(ValidationError, match="not pending"):
        approve_discount(disc, approved_by=bursar_user)
    assert LedgerEntry.objects.count() == before


@pytest.mark.django_db
def test_approving_rejected_discount_raises(school, student, term, issued_invoice, admin_user, bursar_user):
    disc = reject_discount(_req(school, student, term, admin_user), rejected_by=bursar_user, reason="Not eligible")
    with pytest.raises(ValidationError, match="not pending"):
        approve_discount(disc, approved_by=bursar_user)


@pytest.mark.django_db
def test_amount_above_eligible_charges_rejected(school, student, term, issued_invoice, admin_user, bursar_user):
    disc = _req(school, student, term, admin_user, "fixed", "10001.00")
    before = LedgerEntry.objects.count()
    with pytest.raises(ValidationError, match="exceeds eligible charges"):
        approve_discount(disc, approved_by=bursar_user)
    disc.refresh_from_db()
    assert disc.status == Discount.Status.PENDING
    assert LedgerEntry.objects.count() == before


@pytest.mark.django_db
def test_cap_counts_earlier_approved_discounts(school, student, term, issued_invoice, admin_user, bursar_user):
    approve_discount(_req(school, student, term, admin_user, "fixed", "7000.00"), approved_by=bursar_user)
    second = _req(school, student, term, admin_user, "fixed", "3001.00")
    with pytest.raises(ValidationError, match="exceeds eligible charges"):
        approve_discount(second, approved_by=bursar_user)


@pytest.mark.django_db
def test_no_issued_charges_rejected(school, student, term, admin_user, bursar_user):
    disc = _req(school, student, term, admin_user, "fixed", "500.00")
    with pytest.raises(ValidationError, match="No eligible charges"):
        approve_discount(disc, approved_by=bursar_user)


@pytest.mark.django_db
def test_cancelled_invoice_charges_excluded(school, student, term, issued_invoice, admin_user, bursar_user):
    cancel_invoice(issued_invoice, cancelled_by=admin_user, reason="Cancelled")
    disc = _req(school, student, term, admin_user, "percentage", "10.00")
    with pytest.raises(ValidationError, match="No eligible charges"):
        approve_discount(disc, approved_by=bursar_user)


@pytest.mark.django_db
def test_approved_at_and_approved_by_set(school, student, term, issued_invoice, admin_user, bursar_user):
    disc = approve_discount(_req(school, student, term, admin_user), approved_by=bursar_user)
    assert disc.approved_by == bursar_user
    assert disc.approved_at is not None


@pytest.mark.django_db
def test_approve_calls_record_audit_event(monkeypatch, school, student, term, issued_invoice, admin_user, bursar_user):
    calls = []
    monkeypatch.setattr(discounts, "record_audit_event", lambda action, **kw: calls.append((action, kw)))
    disc = approve_discount(_req(school, student, term, admin_user), approved_by=bursar_user)
    assert calls[-1][0] == "discount.approved"
    assert calls[-1][1]["obj"].pk == disc.pk

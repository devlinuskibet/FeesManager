"""Discount request, approval, and rejection workflows wired to the ledger."""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.fees.audit import record_audit_event
from apps.fees.models import Discount, InvoiceLine
from apps.ledger.models import LedgerEntry
from apps.ledger.services import post_entry


def discount_amount(discount: Discount) -> Decimal:
    """Compute the monetary discount amount from eligible non-reversed charges."""
    eligible_qs = LedgerEntry.objects.for_school(discount.school).filter(
        student=discount.student,
        term=discount.term,
        entry_type=LedgerEntry.EntryType.CHARGE,
        reversed_by__isnull=True,
    )
    if discount.fee_item_id:
        line_ids = (
            InvoiceLine.objects.for_school(discount.school)
            .filter(
                fee_item_id=discount.fee_item_id,
            )
            .values_list("id", flat=True)
        )
        eligible_qs = eligible_qs.filter(source_type="invoice_line", source_id__in=line_ids)

    eligible_total = eligible_qs.aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
    if eligible_total <= 0:
        return Decimal("0.00")

    if discount.kind == Discount.Kind.PERCENTAGE:
        return (eligible_total * discount.value / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return discount.value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def request_discount(*, school, student, term, kind, value, requested_by, reason: str, fee_item=None) -> Discount:
    """Create a pending discount request after validating reason and model constraints."""
    if not (reason or "").strip():
        raise ValidationError(_("A non-empty reason is required to request a discount."))

    discount = Discount(
        school=school,
        student=student,
        term=term,
        fee_item=fee_item,
        kind=kind,
        value=value,
        status=Discount.Status.PENDING,
        requested_by=requested_by,
        reason=reason,
    )
    discount.full_clean()
    discount.save()
    record_audit_event("discount.requested", actor=requested_by, obj=discount)
    return discount


def approve_discount(discount: Discount, *, approved_by) -> Discount:
    """Approve a pending discount and post the corresponding credit entry to the ledger."""
    with transaction.atomic():
        disc = Discount.objects.select_for_update().get(pk=discount.pk)
        if disc.status != Discount.Status.PENDING:
            raise ValidationError(_("Discount is not pending."))
        if approved_by.pk == disc.requested_by_id:
            raise ValidationError(_("Requester cannot be the approver."))

        amount = discount_amount(disc)
        if amount <= 0:
            raise ValidationError(_("No eligible charges."))

        all_charges = (
            LedgerEntry.objects.for_school(disc.school)
            .filter(
                student=disc.student,
                term=disc.term,
                entry_type=LedgerEntry.EntryType.CHARGE,
                reversed_by__isnull=True,
            )
            .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        )
        existing_discounts = (
            LedgerEntry.objects.for_school(disc.school)
            .filter(
                student=disc.student,
                term=disc.term,
                entry_type=LedgerEntry.EntryType.DISCOUNT,
                reversed_by__isnull=True,
            )
            .aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]
        )
        if existing_discounts + amount > all_charges:
            raise ValidationError(_("Discount exceeds eligible charges."))

        disc.status = Discount.Status.APPROVED
        disc.approved_by = approved_by
        disc.approved_at = timezone.now()
        disc.full_clean()
        disc.save(update_fields=["status", "approved_by", "approved_at"])

        post_entry(
            school=disc.school,
            student=disc.student,
            term=disc.term,
            entry_type=LedgerEntry.EntryType.DISCOUNT,
            direction=LedgerEntry.Direction.CREDIT,
            amount=amount,
            created_by=approved_by,
            reason=disc.reason,
            reference=f"Discount {disc.id}",
            source_type="discount",
            source_id=disc.id,
        )
        record_audit_event("discount.approved", actor=approved_by, obj=disc)
        return disc


def reject_discount(discount: Discount, *, rejected_by, reason: str) -> Discount:
    """Reject a pending discount with a required reason and no ledger write."""
    if not (reason or "").strip():
        raise ValidationError(_("A non-empty reason is required to reject a discount."))

    with transaction.atomic():
        disc = Discount.objects.select_for_update().get(pk=discount.pk)
        if disc.status != Discount.Status.PENDING:
            raise ValidationError(_("Discount is not pending."))

        disc.status = Discount.Status.REJECTED
        note = f"Rejected by {rejected_by.pk}: {reason.strip()}"
        disc.reason = f"{disc.reason}\n{note}".strip() if disc.reason else note
        disc.full_clean()
        disc.save(update_fields=["status", "reason"])
        record_audit_event("discount.rejected", actor=rejected_by, obj=disc, details={"reason": reason})
        return disc

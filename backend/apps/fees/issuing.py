"""Invoice totals, issuance, and cancellation wired to the append-only ledger."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.fees.audit import record_audit_event
from apps.fees.models import Invoice
from apps.ledger.models import LedgerEntry
from apps.ledger.services import post_entry, reverse_entry


def invoice_total(invoice: Invoice) -> Decimal:
    """Return the exact Decimal sum of all lines on an invoice."""
    return invoice.lines.aggregate(total=Coalesce(Sum("amount"), Decimal("0.00")))["total"]


def issue_invoice(invoice: Invoice, *, issued_by) -> Invoice:
    """Issue a draft invoice and post one debit charge entry per line to the ledger."""
    with transaction.atomic():
        inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if inv.status != Invoice.Status.DRAFT:
            raise ValidationError(_("Only draft invoices can be issued."))

        lines = list(inv.lines.all())
        if not lines:
            raise ValidationError(_("Cannot issue an invoice with no lines."))
        if any(line.amount <= 0 for line in lines):
            raise ValidationError(_("All invoice line amounts must be greater than zero."))

        inv.status = Invoice.Status.ISSUED
        inv.issued_at = timezone.now()
        inv.save(update_fields=["status", "issued_at"])

        for line in lines:
            post_entry(
                school=inv.school,
                student=inv.student,
                term=inv.term,
                entry_type=LedgerEntry.EntryType.CHARGE,
                direction=LedgerEntry.Direction.DEBIT,
                amount=line.amount,
                created_by=issued_by,
                reference=inv.invoice_number,
                source_type="invoice_line",
                source_id=line.id,
            )

        record_audit_event("invoice.issued", actor=issued_by, obj=inv)
        return inv


def cancel_invoice(invoice: Invoice, *, cancelled_by, reason: str) -> Invoice:
    """Cancel a draft or issued invoice, reversing any unreversed ledger charges.

    Note: Handling payments already allocated to an invoice arrives in the reconciliation phase.
    """
    if not (reason or "").strip():
        raise ValidationError(_("A non-empty reason is required to cancel an invoice."))

    with transaction.atomic():
        inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if inv.status == Invoice.Status.CANCELLED:
            raise ValidationError(_("Invoice is already cancelled."))

        if inv.status == Invoice.Status.ISSUED:
            line_ids = list(inv.lines.values_list("id", flat=True))
            charges = LedgerEntry.objects.for_school(inv.school).filter(
                source_type="invoice_line",
                source_id__in=line_ids,
                entry_type=LedgerEntry.EntryType.CHARGE,
            )
            for entry in charges:
                # Skip lines whose charge entry was already reversed earlier.
                if not hasattr(entry, "reversed_by"):
                    reverse_entry(entry, created_by=cancelled_by, reason=reason)

        inv.status = Invoice.Status.CANCELLED
        inv.save(update_fields=["status"])
        record_audit_event("invoice.cancelled", actor=cancelled_by, obj=inv, details={"reason": reason})
        return inv

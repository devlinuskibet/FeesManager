"""Ad-hoc invoice charges and line additions wired to the ledger."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.fees.models import Invoice, InvoiceLine
from apps.fees.numbering import next_invoice_number
from apps.ledger.models import LedgerEntry
from apps.ledger.services import post_entry


def add_invoice_line(
    invoice: Invoice, *, description: str, amount: Decimal, fee_item=None, added_by=None
) -> InvoiceLine:
    """Add a line to a draft or issued invoice; post a ledger charge immediately if issued."""
    with transaction.atomic():
        inv = Invoice.objects.select_for_update().get(pk=invoice.pk)
        if inv.status == Invoice.Status.CANCELLED:
            raise ValidationError(_("Cannot add lines to a cancelled invoice."))
        if amount is None or amount <= 0:
            raise ValidationError(_("Line amount must be greater than zero."))

        line = InvoiceLine(
            school=inv.school,
            invoice=inv,
            fee_item=fee_item,
            description=description,
            amount=amount,
        )
        line.full_clean()
        line.save()

        if inv.status == Invoice.Status.ISSUED:
            post_entry(
                school=inv.school,
                student=inv.student,
                term=inv.term,
                entry_type=LedgerEntry.EntryType.CHARGE,
                direction=LedgerEntry.Direction.DEBIT,
                amount=line.amount,
                created_by=added_by,
                reference=inv.invoice_number,
                source_type="invoice_line",
                source_id=line.id,
            )
        return line


def add_adhoc_charge(
    *, school, student, term, description: str, amount: Decimal, created_by=None, fee_item=None
) -> InvoiceLine:
    """Get or create the student's adhoc invoice for the term and add a charge line."""
    with transaction.atomic():
        inv = (
            Invoice.objects.for_school(school)
            .select_for_update()
            .filter(student=student, term=term, invoice_type=Invoice.InvoiceType.ADHOC)
            .first()
        )
        if inv is None:
            start = date.fromisoformat(term.start_date) if isinstance(term.start_date, str) else term.start_date
            invoice_year = start.year
            invoice_number, sequence = next_invoice_number(school, invoice_year)
            inv = Invoice(
                school=school,
                student=student,
                term=term,
                invoice_number=invoice_number,
                invoice_year=invoice_year,
                sequence=sequence,
                invoice_type=Invoice.InvoiceType.ADHOC,
                status=Invoice.Status.DRAFT,
                created_by=created_by,
            )
            inv.full_clean()
            inv.save()

        return add_invoice_line(
            inv,
            description=description,
            amount=amount,
            fee_item=fee_item,
            added_by=created_by,
        )

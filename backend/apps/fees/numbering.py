"""Sequential invoice numbering per school and year."""

from django.db import transaction

from apps.fees.models import InvoiceSequence


def next_invoice_number(school, year: int) -> tuple[str, int]:
    """Allocate and return the next (invoice_number, sequence) for a school and year."""
    with transaction.atomic():
        # Ensure the counter row exists, then lock it before incrementing.
        seq_row, _ = InvoiceSequence.objects.get_or_create(school=school, year=year)
        seq_row = InvoiceSequence.objects.select_for_update().get(pk=seq_row.pk)
        seq_row.last_value += 1
        seq_row.save(update_fields=["last_value"])
        return f"INV-{year}-{seq_row.last_value:05d}", seq_row.last_value

"""Idempotent term invoice generation from fee structures.

Limitation: Because Invoice is unique on (school, student, term, invoice_type),
a student can have at most one "term" invoice and one "adhoc" invoice per term.
A cancelled term invoice therefore blocks regeneration for that student and term.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from apps.fees.models import FeeStructure, Invoice, InvoiceLine
from apps.fees.numbering import next_invoice_number
from apps.students.models import Student


@dataclass
class GenerationResult:
    """Summary counts and optional dry-run previews from term invoice generation."""

    created: int = 0
    skipped_existing: int = 0
    skipped_no_structure: int = 0
    previews: list[dict] = field(default_factory=list)


def generate_term_invoices(*, school, term, created_by=None, dry_run: bool = False) -> GenerationResult:
    """Generate draft term invoices for all active students in a school."""
    if term.school_id != school.id:
        raise ValidationError(_("Term does not belong to the specified school."))

    result = GenerationResult()
    start = date.fromisoformat(term.start_date) if isinstance(term.start_date, str) else term.start_date
    invoice_year = start.year
    students = (
        Student.objects.for_school(school)
        .filter(status=Student.Status.ACTIVE)
        .select_related("class_stream")
        .order_by("id")
    )

    for student in students:
        structure = FeeStructure.objects.for_school(school).filter(term=term, class_stream=student.class_stream).first()
        if structure is None:
            result.skipped_no_structure += 1
            continue

        if (
            Invoice.objects.for_school(school)
            .filter(student=student, term=term, invoice_type=Invoice.InvoiceType.TERM)
            .exists()
        ):
            result.skipped_existing += 1
            continue

        # Term invoices include only mandatory (non-optional) fee items.
        lines = list(structure.lines.filter(fee_item__is_optional=False).select_related("fee_item"))

        if dry_run:
            total = sum((line.amount for line in lines), Decimal("0.00"))
            result.previews.append(
                {
                    "student_id": student.id,
                    "admission_number": student.admission_number,
                    "total": total,
                }
            )
            continue

        try:
            # Isolate each student in its own transaction so one failure does not roll back others.
            with transaction.atomic():
                invoice_number, sequence = next_invoice_number(school, invoice_year)
                invoice = Invoice(
                    school=school,
                    student=student,
                    term=term,
                    invoice_number=invoice_number,
                    invoice_year=invoice_year,
                    sequence=sequence,
                    invoice_type=Invoice.InvoiceType.TERM,
                    status=Invoice.Status.DRAFT,
                    created_by=created_by,
                )
                invoice.full_clean()
                invoice.save()

                for struct_line in lines:
                    inv_line = InvoiceLine(
                        school=school,
                        invoice=invoice,
                        fee_item=struct_line.fee_item,
                        description=struct_line.fee_item.name,
                        amount=struct_line.amount,
                    )
                    inv_line.full_clean()
                    inv_line.save()
                result.created += 1
        except IntegrityError:
            result.skipped_existing += 1

    return result

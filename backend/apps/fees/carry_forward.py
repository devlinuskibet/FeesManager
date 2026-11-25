"""Term-close balance carry-forward service.

Note: Late payments received after a term is closed are handled in the
reconciliation phase; once a student has a term_close marker entry for a term,
re-running close_term skips that student idempotently.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.fees.audit import record_audit_event
from apps.ledger.balances import student_balance
from apps.ledger.models import LedgerEntry
from apps.ledger.services import post_entry
from apps.students.models import Student


@dataclass
class CarryForwardResult:
    """Summary counts, totals, and optional dry-run previews for close_term."""

    carried_arrears: int = 0
    carried_credits: int = 0
    skipped_zero: int = 0
    skipped_already_carried: int = 0
    total_arrears: Decimal = Decimal("0.00")
    total_credits: Decimal = Decimal("0.00")
    previews: list[dict] = field(default_factory=list)


def _as_date(value) -> date:
    """Convert ISO date strings from un-reloaded test instances to date objects."""
    return date.fromisoformat(value) if isinstance(value, str) else value


def close_term(*, school, term, next_term, closed_by=None, dry_run: bool = False) -> CarryForwardResult:
    """Carry each student's closing term balance forward into next_term."""
    if term.school_id != school.id or next_term.school_id != school.id:
        raise ValidationError(_("Both terms must belong to the specified school."))
    if term.pk == next_term.pk:
        raise ValidationError(_("Closing term and next term must be different."))
    if _as_date(next_term.start_date) <= _as_date(term.start_date):
        raise ValidationError(_("Next term start date must be after the closing term start date."))

    result = CarryForwardResult()
    student_ids = (
        LedgerEntry.objects.for_school(school).filter(term=term).values_list("student_id", flat=True).distinct()
    )
    students = Student.objects.for_school(school).filter(id__in=student_ids).order_by("id")
    ref = f"Carry forward {term.name} to {next_term.name}"

    for student in students:
        with transaction.atomic():
            stu = Student.objects.select_for_update().get(pk=student.pk)
            already_carried = (
                LedgerEntry.objects.for_school(school)
                .filter(
                    student=stu,
                    term=term,
                    entry_type=LedgerEntry.EntryType.CARRY_FORWARD,
                    source_type="term_close",
                    source_id=term.id,
                )
                .exists()
            )
            if already_carried:
                result.skipped_already_carried += 1
                continue

            balance = student_balance(stu, term=term)
            if balance == Decimal("0.00"):
                result.skipped_zero += 1
                continue

            if dry_run:
                result.previews.append(
                    {"student_id": stu.id, "admission_number": stu.admission_number, "balance": balance}
                )
                continue

            if balance > Decimal("0.00"):
                # Arrears: credit closing term to zero it, debit next_term to carry forward.
                post_entry(
                    school=school,
                    student=stu,
                    term=term,
                    entry_type=LedgerEntry.EntryType.CARRY_FORWARD,
                    direction=LedgerEntry.Direction.CREDIT,
                    amount=balance,
                    created_by=closed_by,
                    reference=ref,
                    source_type="term_close",
                    source_id=term.id,
                )
                post_entry(
                    school=school,
                    student=stu,
                    term=next_term,
                    entry_type=LedgerEntry.EntryType.CARRY_FORWARD,
                    direction=LedgerEntry.Direction.DEBIT,
                    amount=balance,
                    created_by=closed_by,
                    reference=ref,
                    source_type="term_close",
                    source_id=term.id,
                )
                result.carried_arrears += 1
                result.total_arrears += balance
            else:
                # Overpayment/credit: debit closing term, credit next_term.
                credit_amount = abs(balance)
                post_entry(
                    school=school,
                    student=stu,
                    term=term,
                    entry_type=LedgerEntry.EntryType.CARRY_FORWARD,
                    direction=LedgerEntry.Direction.DEBIT,
                    amount=credit_amount,
                    created_by=closed_by,
                    reference=ref,
                    source_type="term_close",
                    source_id=term.id,
                )
                post_entry(
                    school=school,
                    student=stu,
                    term=next_term,
                    entry_type=LedgerEntry.EntryType.CARRY_FORWARD,
                    direction=LedgerEntry.Direction.CREDIT,
                    amount=credit_amount,
                    created_by=closed_by,
                    reference=ref,
                    source_type="term_close",
                    source_id=term.id,
                )
                result.carried_credits += 1
                result.total_credits += credit_amount

    if not dry_run:
        record_audit_event("term.closed", actor=closed_by, obj=term, details={"next_term_id": next_term.id})

    return result

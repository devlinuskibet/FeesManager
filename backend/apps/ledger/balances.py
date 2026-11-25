"""Balance and statement queries derived solely from the append-only ledger."""

from decimal import Decimal

from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from apps.academics.models import Term

from .models import LedgerEntry


def student_balance(student, term=None) -> Decimal:
    """Return net balance (debits minus credits) for a student, optionally scoped to a term.

    Positive values mean the student owes fees; negative values mean overpayment/credit.
    """
    qs = LedgerEntry.objects.for_school(student.school).filter(student=student)
    if term is not None:
        qs = qs.filter(term=term)

    totals = qs.aggregate(
        debits=Coalesce(Sum("amount", filter=Q(direction=LedgerEntry.Direction.DEBIT)), Decimal("0.00")),
        credits=Coalesce(Sum("amount", filter=Q(direction=LedgerEntry.Direction.CREDIT)), Decimal("0.00")),
    )
    return totals["debits"] - totals["credits"]


def student_term_balances(student) -> list[tuple[Term, Decimal]]:
    """Return a list of (term, balance) tuples for the student ordered by term start_date."""
    terms = (
        Term.objects.for_school(student.school)
        .filter(ledger_entries__student=student)
        .distinct()
        .order_by("start_date", "term_number")
    )
    return [(term, student_balance(student, term=term)) for term in terms]


def student_statement(student, term=None):
    """Return an ordered queryset of LedgerEntry rows for the student."""
    qs = LedgerEntry.objects.for_school(student.school).filter(student=student)
    if term is not None:
        qs = qs.filter(term=term)
    return qs.order_by("created_at", "id")

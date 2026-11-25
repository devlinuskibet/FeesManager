"""Tests for close_term carry-forward workflow (11 cases)."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.academics.models import Term
from apps.fees.carry_forward import close_term
from apps.ledger.balances import student_balance, student_term_balances
from apps.ledger.models import LedgerEntry
from apps.students.models import Student


@pytest.mark.django_db
def test_arrears_6000_move_to_next_term(school, student, term, next_term, issued_invoice, post_payment, admin_user):
    post_payment(student, term, "4000.00")
    res = close_term(school=school, term=term, next_term=next_term, closed_by=admin_user)
    assert (res.carried_arrears, res.total_arrears) == (1, Decimal("6000.00"))
    assert student_balance(student, term=term) == Decimal("0.00")
    assert student_balance(student, term=next_term) == Decimal("6000.00")
    assert student_balance(student) == Decimal("6000.00")


@pytest.mark.django_db
def test_credit_balance_moves_with_mirrored_directions(
    school, student, term, next_term, issued_invoice, post_payment, admin_user
):
    post_payment(student, term, "12000.00")
    res = close_term(school=school, term=term, next_term=next_term, closed_by=admin_user)
    assert (res.carried_credits, res.total_credits) == (1, Decimal("2000.00"))
    assert student_balance(student, term=term) == Decimal("0.00")
    assert student_balance(student, term=next_term) == Decimal("-2000.00")
    assert student_balance(student) == Decimal("-2000.00")


@pytest.mark.django_db
def test_zero_balance_student_skipped(school, student, term, next_term, issued_invoice, post_payment):
    post_payment(student, term, "10000.00")
    res = close_term(school=school, term=term, next_term=next_term)
    assert res.skipped_zero == 1
    assert res.carried_arrears == res.carried_credits == 0


@pytest.mark.django_db
def test_close_term_twice_posts_nothing_second_time(school, student, term, next_term, issued_invoice):
    assert close_term(school=school, term=term, next_term=next_term).carried_arrears == 1
    count_after_first = LedgerEntry.objects.count()
    second = close_term(school=school, term=term, next_term=next_term)
    assert second.skipped_already_carried == 1
    assert LedgerEntry.objects.count() == count_after_first


@pytest.mark.django_db
def test_dry_run_writes_nothing_and_returns_previews(school, student, term, next_term, issued_invoice):
    before = LedgerEntry.objects.count()
    res = close_term(school=school, term=term, next_term=next_term, dry_run=True)
    assert LedgerEntry.objects.count() == before
    assert res.previews == [
        {"student_id": student.id, "admission_number": student.admission_number, "balance": Decimal("10000.00")}
    ]


@pytest.mark.django_db
def test_other_school_students_untouched(
    school, student, term, next_term, issued_invoice, other_school, other_student, other_school_issued_invoice
):
    close_term(school=school, term=term, next_term=next_term)
    assert LedgerEntry.objects.for_school(other_school).filter(entry_type="carry_forward").count() == 0


@pytest.mark.django_db
def test_term_from_other_school_rejected(school, student, term, next_term, other_term, issued_invoice):
    assert close_term(school=school, term=term, next_term=next_term, dry_run=True).previews
    with pytest.raises(ValidationError, match="Both terms must belong to the specified school"):
        close_term(school=school, term=other_term, next_term=next_term)


@pytest.mark.django_db
def test_same_term_as_next_term_rejected(school, student, term, next_term, issued_invoice):
    assert close_term(school=school, term=term, next_term=next_term, dry_run=True).previews
    with pytest.raises(ValidationError, match="must be different"):
        close_term(school=school, term=term, next_term=term)


@pytest.mark.django_db
def test_next_term_earlier_start_date_rejected(school, academic_year, student, term, next_term, issued_invoice):
    assert close_term(school=school, term=term, next_term=next_term, dry_run=True).previews
    earlier = Term.objects.create(
        school=school,
        name="term_3",
        term_number=3,
        academic_year=academic_year,
        start_date="2023-09-01",
        end_date="2023-11-30",
    )
    with pytest.raises(ValidationError, match="must be after"):
        close_term(school=school, term=term, next_term=earlier)


@pytest.mark.django_db
def test_graduated_student_with_balance_carried(school, student, term, next_term, issued_invoice):
    student.status = Student.Status.GRADUATED
    student.save(update_fields=["status"])
    res = close_term(school=school, term=term, next_term=next_term)
    assert res.carried_arrears == 1
    assert student_balance(student, term=next_term) == Decimal("10000.00")


@pytest.mark.django_db
def test_marker_fields_and_student_term_balances(school, student, term, next_term, issued_invoice):
    close_term(school=school, term=term, next_term=next_term)
    markers = LedgerEntry.objects.for_school(school).filter(entry_type="carry_forward")
    assert markers.count() == 2
    assert all(m.source_type == "term_close" and m.source_id == term.id for m in markers)
    assert student_term_balances(student) == [(term, Decimal("0.00")), (next_term, Decimal("10000.00"))]

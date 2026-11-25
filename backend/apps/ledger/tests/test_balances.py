"""Tests for student_balance, student_term_balances, and student_statement."""

from decimal import Decimal

import pytest

from apps.ledger.balances import student_balance, student_statement, student_term_balances
from apps.ledger.services import post_entry, reverse_entry


@pytest.mark.django_db
def test_balance_charge_payment_discount_and_reversal(school, student, term, admin_user):
    """Charge 10000 - payment 4000 = 6000; discount lowers it; reversal restores it."""
    charge = post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("10000.00"),
    )
    post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="payment",
        direction="credit",
        amount=Decimal("4000.00"),
    )
    assert student_balance(student) == Decimal("6000.00")

    post_entry(
        school=school,
        student=student,
        term=term,
        entry_type="discount",
        direction="credit",
        amount=Decimal("1000.00"),
    )
    assert student_balance(student) == Decimal("5000.00")

    reverse_entry(charge, created_by=admin_user, reason="Wrongly billed")
    assert student_balance(student) == Decimal("-5000.00")


@pytest.mark.django_db
def test_per_term_balances_and_statement(school, student, term, term_2):
    """student_term_balances separates two terms ordered by start_date."""
    post_entry(
        school=school, student=student, term=term, entry_type="charge", direction="debit", amount=Decimal("8000.00")
    )
    post_entry(
        school=school, student=student, term=term_2, entry_type="charge", direction="debit", amount=Decimal("9000.00")
    )
    post_entry(
        school=school, student=student, term=term_2, entry_type="payment", direction="credit", amount=Decimal("2000.00")
    )

    assert student_term_balances(student) == [(term, Decimal("8000.00")), (term_2, Decimal("7000.00"))]
    assert student_statement(student, term=term).count() == 1
    assert student_statement(student).count() == 3


@pytest.mark.django_db
def test_student_and_school_isolation(
    school,
    student,
    other_student_same_school,
    term,
    other_school,
    other_student,
    other_term,
):
    """Other students and other schools never leak into student_balance."""
    post_entry(
        school=school, student=student, term=term, entry_type="charge", direction="debit", amount=Decimal("5000.00")
    )
    post_entry(
        school=school,
        student=other_student_same_school,
        term=term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("9999.00"),
    )
    post_entry(
        school=other_school,
        student=other_student,
        term=other_term,
        entry_type="charge",
        direction="debit",
        amount=Decimal("7777.00"),
    )
    assert student_balance(student) == Decimal("5000.00")
    assert student_balance(other_student) == Decimal("7777.00")


@pytest.mark.django_db
def test_balance_decimal_exactness(school, student, term):
    """0.10 + 0.20 entries sum to exact Decimal('0.30')."""
    post_entry(
        school=school, student=student, term=term, entry_type="charge", direction="debit", amount=Decimal("0.10")
    )
    post_entry(
        school=school, student=student, term=term, entry_type="charge", direction="debit", amount=Decimal("0.20")
    )
    assert student_balance(student) == Decimal("0.30")

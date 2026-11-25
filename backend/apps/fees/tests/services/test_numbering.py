"""Tests for sequential per-school, per-year invoice numbering."""

import pytest

from apps.fees.numbering import next_invoice_number


@pytest.mark.django_db
def test_first_number_for_school_and_year(school):
    """First number for a school and year is INV-2027-00001."""
    number, seq = next_invoice_number(school, 2027)
    assert number == "INV-2027-00001"
    assert seq == 1


@pytest.mark.django_db
def test_second_number_increments(school):
    """Second call for the same school and year returns 00002."""
    next_invoice_number(school, 2027)
    number, seq = next_invoice_number(school, 2027)
    assert number == "INV-2027-00002"
    assert seq == 2


@pytest.mark.django_db
def test_different_school_starts_at_one(school, other_school):
    """A second school has its own independent sequence starting at 00001."""
    next_invoice_number(school, 2027)
    number, seq = next_invoice_number(other_school, 2027)
    assert number == "INV-2027-00001"
    assert seq == 1


@pytest.mark.django_db
def test_different_year_starts_at_one(school):
    """A new year for the same school starts at 00001 again."""
    next_invoice_number(school, 2027)
    number, seq = next_invoice_number(school, 2028)
    assert number == "INV-2028-00001"
    assert seq == 1


@pytest.mark.django_db
def test_format_zero_padded_five_digits(school):
    """Invoice number sequence is zero-padded to five digits."""
    number, seq = next_invoice_number(school, 2027)
    assert seq == 1
    assert number.endswith("-00001")
    assert len(number.split("-")[-1]) == 5

"""Fixtures for discount and carry-forward workflow tests."""

from decimal import Decimal

import pytest

from apps.academics.models import Term
from apps.fees.issuing import issue_invoice
from apps.fees.models import FeeItem, Invoice, InvoiceLine
from apps.ledger.services import post_entry
from apps.students.models import Student


@pytest.fixture
def issued_invoice(school, student, term, fee_item, admin_user):
    """Issued invoice totalling 10000.00 (6000.00 on fee_item + 4000.00 on BD01)."""
    boarding = FeeItem.objects.create(school=school, code="BD01", name="Boarding")
    inv = Invoice.objects.create(
        school=school,
        student=student,
        term=term,
        invoice_number="INV-2024-00100",
        invoice_year=2024,
        sequence=100,
        invoice_type=Invoice.InvoiceType.TERM,
        created_by=admin_user,
    )
    InvoiceLine.objects.create(
        school=school, invoice=inv, fee_item=fee_item, description="Tuition", amount=Decimal("6000.00")
    )
    InvoiceLine.objects.create(
        school=school, invoice=inv, fee_item=boarding, description="Boarding", amount=Decimal("4000.00")
    )
    return issue_invoice(inv, issued_by=admin_user)


@pytest.fixture
def next_term(school, academic_year):
    """Second term in the default school starting after the default term."""
    return Term.objects.create(
        school=school,
        name="term_2",
        term_number=2,
        academic_year=academic_year,
        start_date="2024-05-06",
        end_date="2024-08-02",
    )


@pytest.fixture
def second_student(school, class_stream):
    """A second active student in the default school."""
    return Student.objects.create(
        school=school,
        admission_number="ADM010",
        first_name="Grace",
        last_name="Mutua",
        class_stream=class_stream,
        status=Student.Status.ACTIVE,
        date_admitted="2024-01-15",
    )


@pytest.fixture
def other_school_issued_invoice(other_school, other_student, other_term, other_fee_item, admin_user):
    """An issued invoice of 5000.00 in other_school."""
    inv = Invoice.objects.create(
        school=other_school,
        student=other_student,
        term=other_term,
        invoice_number="INV-2024-00100",
        invoice_year=2024,
        sequence=100,
        invoice_type=Invoice.InvoiceType.TERM,
        created_by=admin_user,
    )
    InvoiceLine.objects.create(
        school=other_school, invoice=inv, fee_item=other_fee_item, description="Tuition", amount=Decimal("5000.00")
    )
    return issue_invoice(inv, issued_by=admin_user)


@pytest.fixture
def post_payment(admin_user):
    """Helper to post a payment credit entry to the ledger."""

    def _post(student, term, amount, reference="MPESA-001"):
        return post_entry(
            school=student.school,
            student=student,
            term=term,
            entry_type="payment",
            direction="credit",
            amount=Decimal(amount),
            created_by=admin_user,
            reference=reference,
        )

    return _post

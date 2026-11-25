"""
Models for the `fees` app – step 2a.
All business models inherit `TenantMixin` to guarantee tenant scoping.
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import TenantMixin


class FeeItem(TenantMixin):
    """A fee item, e.g. tuition, boarding.

    `code` is unique per school. `is_optional` indicates whether the fee may be omitted.
    """

    code = models.CharField(_("code"), max_length=20)
    name = models.CharField(_("name"), max_length=100)
    is_optional = models.BooleanField(_("optional"), default=False)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        unique_together = ("school", "code")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"


class FeeStructure(TenantMixin):
    """A fee structure for a given term and class stream.

    One record per (school, term, class_stream).
    """

    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.PROTECT,
        related_name="fee_structures",
        verbose_name=_("term"),
    )
    class_stream = models.ForeignKey(
        "academics.ClassStream",
        on_delete=models.PROTECT,
        related_name="fee_structures",
        verbose_name=_("class stream"),
    )

    class Meta:
        unique_together = ("school", "term", "class_stream")
        ordering = ["school", "term", "class_stream"]

    def clean(self) -> None:
        super().clean()
        # Tenant consistency: term and class stream must belong to the structure's school.
        # Guards use *_id so a missing relation is reported by field validation, not a crash.
        if self.school_id:
            if self.term_id and self.term.school_id != self.school_id:
                raise ValidationError(_("Term belongs to a different school than the fee structure."))
            if self.class_stream_id and self.class_stream.school_id != self.school_id:
                raise ValidationError(_("Class stream belongs to a different school than the fee structure."))

    def __str__(self) -> str:
        return f"FeeStructure {self.school.name} – {self.term} – {self.class_stream}"


class FeeStructureLine(TenantMixin):
    """Link a `FeeItem` to a `FeeStructure` with an amount.

    Uniqueness enforced on (fee_structure, fee_item).
    """

    fee_structure = models.ForeignKey(
        FeeStructure,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name=_("fee structure"),
    )
    fee_item = models.ForeignKey(
        FeeItem,
        on_delete=models.PROTECT,
        related_name="structure_lines",
        verbose_name=_("fee item"),
    )
    amount = models.DecimalField(
        _("amount"), max_digits=12, decimal_places=2, help_text=_("Money amount with 2 decimal places.")
    )

    class Meta:
        unique_together = ("fee_structure", "fee_item")
        ordering = ["fee_structure", "fee_item"]

    def __str__(self) -> str:
        return f"{self.fee_item.code} @ {self.amount} for {self.fee_structure}"

    def clean(self) -> None:
        super().clean()
        # Tenant consistency: the line, its fee structure and its fee item share one school.
        if self.school_id:
            if self.fee_structure_id and self.fee_structure.school_id != self.school_id:
                raise ValidationError(_("Line and fee structure belong to different schools."))
            if self.fee_item_id and self.fee_item.school_id != self.school_id:
                raise ValidationError(_("Line and fee item belong to different schools."))


class Invoice(TenantMixin):
    """Invoice generated for a student per term.

    `invoice_number` format is ``INV-{year}-{sequence:05d}`` – the generator lives in step 2c.
    """

    class InvoiceType(models.TextChoices):
        TERM = "term", _("term")
        ADHOC = "adhoc", _("adhoc")

    class Status(models.TextChoices):
        DRAFT = "draft", _("draft")
        ISSUED = "issued", _("issued")
        CANCELLED = "cancelled", _("cancelled")

    invoice_number = models.CharField(_("invoice number"), max_length=32)
    invoice_year = models.PositiveSmallIntegerField(_("invoice year"))
    sequence = models.PositiveIntegerField(_("sequence"))
    invoice_type = models.CharField(_("type"), max_length=10, choices=InvoiceType.choices)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.DRAFT)
    issued_at = models.DateTimeField(_("issued at"), null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("created by"),
    )

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="invoices",
        verbose_name=_("student"),
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name=_("term"),
    )

    class Meta:
        unique_together = ("school", "student", "term", "invoice_type")
        constraints = [
            models.UniqueConstraint(fields=["school", "invoice_number"], name="fees_inv_num_uni"),
            models.UniqueConstraint(fields=["school", "invoice_year", "sequence"], name="fees_inv_seq_uni"),
        ]
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        return f"Invoice {self.invoice_number} for {self.student.admission_number}"

    def clean(self) -> None:
        super().clean()
        # Tenant consistency: student and term must belong to the invoice's school.
        if self.school_id:
            if self.student_id and self.student.school_id != self.school_id:
                raise ValidationError(_("Student belongs to a different school than the invoice."))
            if self.term_id and self.term.school_id != self.school_id:
                raise ValidationError(_("Term belongs to a different school than the invoice."))


class InvoiceLine(TenantMixin):
    """Line item on an `Invoice`.

    `fee_item` may be null for ad‑hoc charges.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="lines",
        verbose_name=_("invoice"),
    )
    fee_item = models.ForeignKey(
        FeeItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoice_lines",
        verbose_name=_("fee item"),
    )
    description = models.TextField(_("description"), blank=True)
    amount = models.DecimalField(
        _("amount"), max_digits=12, decimal_places=2, help_text=_("Money amount with 2 decimal places.")
    )

    class Meta:
        ordering = ["invoice", "id"]

    def __str__(self) -> str:
        return f"Line {self.id} on {self.invoice.invoice_number}"

    def clean(self) -> None:
        super().clean()
        # Tenant consistency: the line, its invoice and its fee item (if any) share one school.
        if self.school_id:
            if self.invoice_id and self.invoice.school_id != self.school_id:
                raise ValidationError(_("Invoice belongs to a different school than the line."))
            if self.fee_item_id and self.fee_item.school_id != self.school_id:
                raise ValidationError(_("FeeItem belongs to a different school than the line."))


class Discount(TenantMixin):
    """Discount applied to a student for a term.

    `kind` determines whether `value` is a fixed amount or a percentage.
    """

    class Kind(models.TextChoices):
        FIXED = "fixed", _("fixed")
        PERCENTAGE = "percentage", _("percentage")

    class Status(models.TextChoices):
        PENDING = "pending", _("pending")
        APPROVED = "approved", _("approved")
        REJECTED = "rejected", _("rejected")

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="discounts",
        verbose_name=_("student"),
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.PROTECT,
        related_name="discounts",
        verbose_name=_("term"),
    )
    fee_item = models.ForeignKey(
        FeeItem,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="discounts",
        verbose_name=_("fee item (optional)"),
    )
    kind = models.CharField(_("kind"), max_length=10, choices=Kind.choices)
    value = models.DecimalField(_("value"), max_digits=12, decimal_places=2)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.PENDING)
    requested_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="requested_discounts",
        verbose_name=_("requested by"),
    )
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_discounts",
        verbose_name=_("approved by"),
    )
    approved_at = models.DateTimeField(_("approved at"), null=True, blank=True)
    reason = models.TextField(_("reason"), blank=True)

    class Meta:
        indexes = [models.Index(fields=["school", "student", "term"], name="fees_discount_idx")]
        ordering = ["-approved_at"]

    def __str__(self) -> str:
        return f"Discount {self.id} for {self.student.admission_number}"

    def clean(self) -> None:
        super().clean()
        # Value rules: always positive; a percentage may not exceed 100.
        if self.value is not None:
            if self.value <= 0:
                raise ValidationError(_("Discount value must be positive."))
            if self.kind == self.Kind.PERCENTAGE and self.value > 100:
                raise ValidationError(_("Percentage value must be between 0 and 100."))
        # Tenant consistency: student, term and fee item must belong to the discount's school.
        if self.school_id:
            if self.student_id and self.student.school_id != self.school_id:
                raise ValidationError(_("Student belongs to a different school than the discount."))
            if self.term_id and self.term.school_id != self.school_id:
                raise ValidationError(_("Term belongs to a different school than the discount."))
            if self.fee_item_id and self.fee_item.school_id != self.school_id:
                raise ValidationError(_("FeeItem belongs to a different school than the discount."))
        # Approval trail: the requester cannot approve their own request.
        if self.approved_by_id and self.requested_by_id == self.approved_by_id:
            raise ValidationError(_("Requester cannot be the approver."))


class InvoiceSequence(TenantMixin):
    """Per-school, per-year counter for sequential invoice numbering."""

    year = models.PositiveSmallIntegerField(_("year"))
    last_value = models.PositiveIntegerField(_("last value"), default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["school", "year"], name="fees_invseq_uni"),
        ]
        ordering = ["school", "year"]

    def __str__(self) -> str:
        return f"{self.school_id}-{self.year}: {self.last_value}"

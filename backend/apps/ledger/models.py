"""Append-only student fee ledger models."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import School, TenantMixin

from .exceptions import LedgerImmutableError
from .querysets import LedgerEntryManager


class LedgerEntry(TenantMixin):
    """Immutable double-entry-style ledger row for a student's fee account."""

    class EntryType(models.TextChoices):
        CHARGE = "charge", _("charge")
        PAYMENT = "payment", _("payment")
        DISCOUNT = "discount", _("discount")
        WAIVER = "waiver", _("waiver")
        REVERSAL = "reversal", _("reversal")
        ADJUSTMENT = "adjustment", _("adjustment")
        CARRY_FORWARD = "carry_forward", _("carry_forward")

    class Direction(models.TextChoices):
        DEBIT = "debit", _("debit")
        CREDIT = "credit", _("credit")

    # Override TenantMixin.school with PROTECT so deleting a school cannot cascade-delete ledger rows.
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="%(class)ss",
        verbose_name=_("school"),
        db_index=True,
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="ledger_entries",
        verbose_name=_("student"),
    )
    term = models.ForeignKey(
        "academics.Term",
        on_delete=models.PROTECT,
        related_name="ledger_entries",
        verbose_name=_("term"),
    )
    entry_type = models.CharField(_("entry type"), max_length=20, choices=EntryType.choices)
    direction = models.CharField(_("direction"), max_length=10, choices=Direction.choices)
    amount = models.DecimalField(
        _("amount"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    source_type = models.CharField(_("source type"), max_length=50, blank=True)
    source_id = models.PositiveBigIntegerField(_("source id"), null=True, blank=True)
    reference = models.CharField(_("reference"), max_length=100, blank=True)
    reason = models.TextField(_("reason"), blank=True)
    reverses = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversed_by",
        verbose_name=_("reverses"),
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("created by"),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    objects = LedgerEntryManager

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["school", "student", "term"], name="ledger_student_term_idx"),
            models.Index(fields=["school", "entry_type"], name="ledger_type_idx"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="ledger_amount_positive"),
        ]

    def __str__(self) -> str:
        return f"LedgerEntry({self.entry_type}, {self.direction}, {self.amount})"

    def clean(self) -> None:
        super().clean()
        # Tenant consistency: student and term must belong to the entry's school.
        if self.school_id:
            if self.student_id and self.student.school_id != self.school_id:
                raise ValidationError(_("Student belongs to a different school than the ledger entry."))
            if self.term_id and self.term.school_id != self.school_id:
                raise ValidationError(_("Term belongs to a different school than the ledger entry."))

        # Direction rules by entry_type.
        if self.entry_type == self.EntryType.CHARGE and self.direction != self.Direction.DEBIT:
            raise ValidationError(_("Charge entries must have direction 'debit'."))
        if self.entry_type in (self.EntryType.PAYMENT, self.EntryType.DISCOUNT, self.EntryType.WAIVER):
            if self.direction != self.Direction.CREDIT:
                raise ValidationError(_("Payment, discount, and waiver entries must have direction 'credit'."))

        # Reversal link rules: reverses is required iff entry_type is 'reversal'.
        is_reversal = self.entry_type == self.EntryType.REVERSAL
        if is_reversal and not self.reverses_id:
            raise ValidationError(_("Reversal entries must reference the entry being reversed."))
        if not is_reversal and self.reverses_id:
            raise ValidationError(_("Only reversal entries may reference another entry via 'reverses'."))

        if is_reversal and self.reverses_id:
            target = self.reverses
            if target.entry_type == self.EntryType.REVERSAL:
                raise ValidationError(_("Cannot reverse a reversal entry."))
            if (
                target.school_id != self.school_id
                or target.student_id != self.student_id
                or target.term_id != self.term_id
                or target.amount != self.amount
            ):
                raise ValidationError(_("Reversal must match target school, student, term, and amount."))
            if self.direction == target.direction:
                raise ValidationError(_("Reversal must have the opposite direction of the entry it reverses."))
            if not (self.reason or "").strip():
                raise ValidationError(_("A non-empty reason is required for reversal entries."))

    def save(self, *args, **kwargs) -> None:
        """Enforce append-only semantics: block updates, validate every insert."""
        if self.pk is not None and not self._state.adding:
            raise LedgerImmutableError.for_operation("modify")
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs) -> None:
        """Block row-level deletes."""
        raise LedgerImmutableError.for_operation("delete")

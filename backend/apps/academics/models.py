"""
Academic structure models.

Defines AcademicYear, Term, and ClassStream. Every model is tenant-scoped via
TenantMixin (a school foreign key with a DB index). Querysets must always be
scoped to a school using .for_school(school) to enforce tenant isolation.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import TenantMixin


class AcademicYear(TenantMixin):
    """A school year (e.g. 2027).

    A school may have many academic years, but only one should be current at
    a time. The is_current flag is enforced at the application level (and
    could be promoted to a partial unique index in PostgreSQL later).
    """

    name = models.CharField(
        _("year name"),
        max_length=50,
        help_text="e.g. '2027' or '2027-2028'",
    )
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    is_current = models.BooleanField(
        _("current year"),
        default=False,
        help_text="Whether this is the school's current academic year.",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("academic year")
        verbose_name_plural = _("academic years")
        ordering = ["-start_date", "name"]
        unique_together = ("school", "name")
        indexes = [
            models.Index(
                fields=["school", "is_current"],
                name="ay_school_current_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.school.slug})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_date > self.end_date:
            raise ValidationError(_("End date must be after start date."))
        # Only one current academic year per school.
        if self.is_current:
            qs = AcademicYear.objects.for_school(self.school).filter(is_current=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(_("An academic year is already marked current for this school."))


class Term(TenantMixin):
    """A term within an academic year (e.g. Term 1, 2027).

    Exactly one term per school should be active at any time. Dates must fall
    within the parent academic year's range.
    """

    class TermName(models.TextChoices):
        TERM_1 = "term_1", _("Term 1")
        TERM_2 = "term_2", _("Term 2")
        TERM_3 = "term_3", _("Term 3")

    name = models.CharField(
        _("term name"),
        max_length=20,
        choices=TermName.choices,
    )
    term_number = models.PositiveSmallIntegerField(
        _("term number"),
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="1, 2, 3, or 4.",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="terms",
        verbose_name=_("academic year"),
    )
    start_date = models.DateField(_("start date"))
    end_date = models.DateField(_("end date"))
    is_active = models.BooleanField(
        _("active term"),
        default=False,
        help_text="Whether this is the school's currently active term.",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("term")
        verbose_name_plural = _("terms")
        ordering = ["academic_year", "term_number"]
        unique_together = ("school", "academic_year", "term_number")
        indexes = [
            models.Index(
                fields=["school", "is_active"],
                name="t_school_active_idx",
            ),
            models.Index(
                fields=["school", "academic_year"],
                name="t_school_year_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_name_display()} {self.academic_year.name} ({self.school.slug})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_date > self.end_date:
            raise ValidationError(_("End date must be after start date."))
        # Dates must be within the parent academic year.
        if self.academic_year_id:
            ay = AcademicYear.objects.filter(pk=self.academic_year_id).first()
            if ay:
                if self.start_date < ay.start_date:
                    raise ValidationError(_("Term start date cannot be before the academic year start date."))
                if self.end_date > ay.end_date:
                    raise ValidationError(_("Term end date cannot be after the academic year end date."))
        # Only one active term per school.
        if self.is_active:
            qs = Term.objects.for_school(self.school).filter(is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(_("A term is already marked active for this school."))


class ClassStream(TenantMixin):
    """A class/stream combination (e.g. Form 1 East, Grade 7).

    'level' is the year group (Form 1, Grade 7, etc.) and 'stream' is the
    subdivision (East, West, A, B, etc.). Together with the school they form
    a unique teaching group.
    """

    name = models.CharField(
        _("class/stream name"),
        max_length=100,
        help_text="e.g. 'Form 1 East', 'Grade 7'",
    )
    level = models.CharField(
        _("level"),
        max_length=50,
        help_text="Year group, e.g. 'Form 1', 'Grade 7', 'Year 9'.",
    )
    stream = models.CharField(
        _("stream"),
        max_length=50,
        blank=True,
        help_text="Subdivision within the level, e.g. 'East', 'A'.",
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.PROTECT,
        related_name="class_streams",
        verbose_name=_("academic year"),
    )
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("class/stream")
        verbose_name_plural = _("class/streams")
        ordering = ["level", "stream", "name"]
        unique_together = ("school", "level", "stream", "academic_year")
        indexes = [
            models.Index(
                fields=["school", "is_active"],
                name="cs_school_active_idx",
            ),
            models.Index(
                fields=["school", "academic_year"],
                name="cs_school_year_idx",
            ),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-build name from level + stream if not explicitly set.
        if not self.name:
            self.name = f"{self.level} {self.stream}".strip()
        super().save(*args, **kwargs)

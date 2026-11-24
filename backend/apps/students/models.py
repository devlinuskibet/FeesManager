"""
Student and guardian models.

Student: admission number unique per school, full name, class stream, status,
date admitted. Guardian: name, E.164 phone, relationship, primary flag.
StudentGuardian: the many-to-many link between students and guardians with a
primary flag.

All models are tenant-scoped via TenantMixin.
"""

import re

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.academics.models import ClassStream
from apps.tenants.models import TenantMixin

# E.164: optional +, country code, up to 15 digits. Kenyan numbers: +2547XXXXXXXX.
PHONE_REGEX = re.compile(r"^\+?[1-9]\d{1,14}$")
validate_phone = RegexValidator(
    PHONE_REGEX,
    _("Phone number must be in E.164 format, e.g. +254712345678."),
)


class Student(TenantMixin):
    """A student enrolled at a school.

    Admission number is unique per school. It is normalized (trimmed, uppercased,
    internal whitespace collapsed) on save so that 'ADM 001', 'adm001', and
    'ADM001' all resolve to the same value.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        TRANSFERRED = "transferred", _("Transferred")
        GRADUATED = "graduated", _("Graduated")
        SUSPENDED = "suspended", _("Suspended")

    admission_number = models.CharField(
        _("admission number"),
        max_length=50,
        db_index=True,
        help_text="Unique per school. Normalized to uppercase on save.",
    )
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100)
    class_stream = models.ForeignKey(
        ClassStream,
        on_delete=models.PROTECT,
        related_name="students",
        verbose_name=_("class/stream"),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    date_admitted = models.DateField(_("date admitted"))
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("student")
        verbose_name_plural = _("students")
        ordering = ["admission_number"]
        unique_together = ("school", "admission_number")
        indexes = [
            models.Index(
                fields=["school", "status"],
                name="s_school_status_idx",
            ),
            models.Index(
                fields=["school", "class_stream"],
                name="s_school_class_idx",
            ),
        ]

    def __str__(self):
        return f"{self.admission_number} — {self.full_name}"

    @property
    def full_name(self):
        """First + last name."""
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        # Normalize admission number: trim, collapse internal whitespace,
        # uppercase. This makes 'ADM 001', 'adm 001', 'ADM001' identical.
        if self.admission_number:
            self.admission_number = re.sub(r"\s+", "", self.admission_number.strip()).upper()
        super().save(*args, **kwargs)


class Guardian(TenantMixin):
    """A parent or guardian of one or more students.

    Phone is stored in E.164 format. A guardian can be linked to multiple
    students (e.g. siblings) via StudentGuardian.
    """

    class Relationship(models.TextChoices):
        MOTHER = "mother", _("Mother")
        FATHER = "father", _("Father")
        GUARDIAN = "guardian", _("Guardian")
        OTHER = "other", _("Other")

    name = models.CharField(_("name"), max_length=200)
    phone = models.CharField(
        _("phone number"),
        max_length=20,
        validators=[validate_phone],
        help_text="E.164 format, e.g. +254712345678.",
    )
    relationship = models.CharField(
        _("relationship"),
        max_length=20,
        choices=Relationship.choices,
        default=Relationship.GUARDIAN,
    )
    is_primary = models.BooleanField(
        _("primary contact"),
        default=False,
        help_text="Whether this is the primary guardian for their linked students.",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("guardian")
        verbose_name_plural = _("guardians")
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["school", "phone"],
                name="g_school_phone_idx",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class StudentGuardian(TenantMixin):
    """Links a student to a guardian.

    A student may have multiple guardians; a guardian may have multiple
    students. The primary flag marks the main contact for that student.
    """

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="guardian_links",
        verbose_name=_("student"),
    )
    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.CASCADE,
        related_name="student_links",
        verbose_name=_("guardian"),
    )
    is_primary = models.BooleanField(_("primary"), default=False)
    relationship = models.CharField(
        _("relationship override"),
        max_length=20,
        blank=True,
        help_text="Optional relationship specific to this student link.",
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("student guardian link")
        verbose_name_plural = _("student guardian links")
        unique_together = ("student", "guardian")
        indexes = [
            models.Index(
                fields=["student", "is_primary"],
                name="sg_student_primary_idx",
            ),
            models.Index(
                fields=["guardian", "is_primary"],
                name="sg_guardian_primary_idx",
            ),
        ]

    def __str__(self):
        return f"{self.student.admission_number} — {self.guardian.name}"

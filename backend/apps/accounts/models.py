"""
Custom user model, roles, and memberships.

- User: email-based (USERNAME_FIELD = email). A user exists globally but only
  gains access to a school through an active Membership.
- Role: role type scoped to a school (school_admin, bursar, accountant,
  parent).
- Membership: links a user to a school with a role. A user normally has one
  active membership; superusers span all schools.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """System user. Login is by email; username is kept for AbstractUser
    compatibility and defaults to the email."""

    email = models.EmailField(_("email address"), unique=True, db_index=True)
    phone = models.CharField(
        _("phone number"),
        max_length=30,
        blank=True,
        help_text="International format, e.g. +2547XXXXXXXX",
    )
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
        help_text="Whether the user's email/phone has been verified (OTP, etc.)",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta(AbstractUser.Meta):
        verbose_name = _("user")
        verbose_name_plural = _("users")
        indexes = [
            models.Index(fields=["email"], name="accounts_user_email_idx"),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """First + last name, falling back to the email."""
        full = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return full or self.email


class Role(models.Model):
    """A role within a single school.

    RoleType choices map to the permission classes in apps.accounts.permissions.
    """

    class RoleType(models.TextChoices):
        SCHOOL_ADMIN = "school_admin", _("School Admin")
        BURSAR = "bursar", _("Bursar")
        ACCOUNTANT = "accountant", _("Accountant")
        PARENT = "parent", _("Parent/Guardian")

    name = models.CharField(_("role name"), max_length=50, choices=RoleType.choices)
    school = models.ForeignKey(
        "tenants.School",
        on_delete=models.CASCADE,
        related_name="roles",
        verbose_name=_("school"),
    )
    description = models.TextField(_("description"), blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        unique_together = ("name", "school")
        indexes = [
            models.Index(fields=["school", "name"], name="accounts_role_school_name_idx"),
        ]

    def __str__(self):
        return f"{self.get_name_display()} ({self.school.slug})"


class Membership(models.Model):
    """A user's role within a school.

    Permissions resolve against request.school -> user's active membership(s)
    in that school.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("user"),
    )
    school = models.ForeignKey(
        "tenants.School",
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("school"),
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("role"),
    )
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("membership")
        verbose_name_plural = _("memberships")
        unique_together = ("user", "school", "role")
        indexes = [
            models.Index(fields=["user", "is_active"], name="membership_user_active_idx"),
            models.Index(
                fields=["school", "is_active"],
                name="membership_school_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} @ {self.school.slug} ({self.role.name})"

    @property
    def role_type(self):
        return self.role.name

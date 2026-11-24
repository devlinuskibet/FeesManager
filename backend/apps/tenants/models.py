"""
Multi-tenancy core.

Defines the School model and TenantMixin, an abstract base that adds a
school foreign key (with DB index) to every business table. Tenant isolation
is enforced at the queryset/manager layer, not by row-level security, so the
same code works on any PostgreSQL version.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import TenantManager


class School(models.Model):
    """A school, college, or TVET institution.

    Every business record in the system scopes to exactly one school. A
    superuser can span schools; an ordinary user belongs to one school via
    apps.accounts.Membership.
    """

    name = models.CharField(_("school name"), max_length=200)
    slug = models.SlugField(
        _("slug"),
        unique=True,
        max_length=100,
        help_text=("Unique URL-friendly identifier, e.g. 'light-bridge-academy'. Used for tenant routing."),
    )
    email = models.EmailField(_("contact email"), blank=True)
    phone = models.CharField(_("contact phone"), max_length=30, blank=True)
    address = models.TextField(_("address"), blank=True)
    city = models.CharField(_("city"), max_length=100, blank=True)
    county = models.CharField(_("county"), max_length=100, blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("school")
        verbose_name_plural = _("schools")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"], name="tenants_school_slug_idx"),
            models.Index(fields=["is_active"], name="tenants_school_active_idx"),
        ]

    def __str__(self):
        return self.name


class TenantMixin(models.Model):
    """Abstract base for all tenant-scoped models.

    Subclasses automatically get a `school` foreign key and DB index.
    Querysets should call .for_school(school) to enforce isolation.
    """

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        verbose_name=_("school"),
        db_index=True,
    )

    objects = TenantManager()

    class Meta:
        abstract = True

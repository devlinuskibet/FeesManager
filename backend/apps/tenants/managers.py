"""
Tenant-scoped queryset managers.

TenantQuerySet.for_school() is the single place where tenant filtering is
applied. Views and services must always scope queries to a school; the only
bypass is an explicit superuser check in permissions/services.
"""

from django.db import models


class TenantQuerySet(models.QuerySet):
    """Queryset with tenant-scoping helpers."""

    def for_school(self, school):
        """Return rows belonging to school.

        A None school returns an empty queryset — never leak data by default.
        """
        if school is None:
            return self.none()
        return self.filter(school=school)

    def accessible_by(self, user, school=None):
        """Rows visible to user within school.

        Superusers see every row in the requested school; all other users see
        nothing unless a more specific permission grants access.
        """
        if user.is_authenticated and user.is_superuser:
            if school is not None:
                return self.for_school(school)
            return self.all()
        return self.none()


class TenantManager(models.Manager):
    """Manager exposing TenantQuerySet helpers."""

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def for_school(self, school):
        return self.get_queryset().for_school(school)

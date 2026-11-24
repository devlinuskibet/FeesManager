"""
Role-based permissions scoped to the current school (request.school).

request.school is set by apps.tenants.middleware.TenantMiddleware from the
X-School-ID header. Superusers bypass all school-scoped checks.
"""

from rest_framework import permissions


class IsSchoolMember(permissions.BasePermission):
    """Authenticated user with an active membership in request.school."""

    message = "You do not belong to the selected school."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        school = getattr(request, "school", None)
        if school is None:
            return False
        return user.memberships.filter(school=school, is_active=True).exists()


class RolePermission(permissions.BasePermission):
    """
    Require one of the given role types (Role.RoleType values) in request.school.

    Usage::

        permission_classes = [IsSchoolMember, RolePermission(["bursar"])]
    """

    def __init__(self, allowed_roles=None):
        self.allowed_roles = list(allowed_roles or [])

    def has_permission(self, request, view):
        if not IsSchoolMember().has_permission(request, view):
            return False
        user = request.user
        if user.is_superuser:
            return True
        school = getattr(request, "school", None)
        return user.memberships.filter(school=school, is_active=True, role__name__in=self.allowed_roles).exists()


class IsSchoolAdmin(RolePermission):
    """Full access: user management, settings, school onboarding."""

    def __init__(self):
        super().__init__(["school_admin"])


class IsBursar(RolePermission):
    """All finance operations: reconciliation, reports, waivers."""

    def __init__(self):
        super().__init__(["school_admin", "bursar"])


class IsAccountant(RolePermission):
    """Read-mostly: reports and exports."""

    def __init__(self):
        super().__init__(["school_admin", "bursar", "accountant"])


class IsParent(RolePermission):
    """Parent/guardian portal: read-only access to their own children."""

    def __init__(self):
        super().__init__(["school_admin", "bursar", "accountant", "parent"])

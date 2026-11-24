"""Views for the tenants app."""

from rest_framework import generics

from apps.accounts.models import Membership, Role
from apps.accounts.permissions import IsSchoolAdmin

from .models import School
from .serializers import SchoolSerializer


class SchoolListCreateView(generics.ListCreateAPIView):
    """List schools visible to the caller, or create a new school.

    Creating a school automatically grants the caller the School Admin role
    on that school (they become the school's first administrator).
    """

    serializer_class = SchoolSerializer
    permission_classes = [IsSchoolAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return School.objects.all()
        # Ordinary users see schools they have an active membership in.
        return School.objects.filter(memberships__user=user, memberships__is_active=True).distinct()

    def perform_create(self, serializer):
        school = serializer.save()
        # Make the creator the school's first admin.
        role, _created = Role.objects.get_or_create(
            name="school_admin",
            school=school,
            defaults={"description": "Full access to the school"},
        )
        Membership.objects.create(user=self.request.user, school=school, role=role, is_active=True)

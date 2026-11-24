"""Views for the academics app.

All viewsets scope their querysets to request.school (set by TenantMiddleware)
so that users can only see their own school's academic data.
"""

from rest_framework import viewsets

from apps.accounts.permissions import IsAccountant, IsBursar

from .models import AcademicYear, ClassStream, Term
from .serializers import AcademicYearSerializer, ClassStreamSerializer, TermSerializer


class AcademicYearViewSet(viewsets.ModelViewSet):
    """CRUD for AcademicYear."""

    serializer_class = AcademicYearSerializer
    permission_classes = [IsAccountant]  # read-mostly; write handled below
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_permissions(self):
        # SchoolAdmin/Bursar can write; Accountant (and above) can read.
        if self.action in ("list", "retrieve"):
            self.permission_classes = [IsAccountant]
        else:
            self.permission_classes = [IsBursar]
        return super().get_permissions()

    def get_queryset(self):
        school = getattr(self.request, "school", None)
        return AcademicYear.objects.for_school(school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.school)

    def perform_update(self, serializer):
        serializer.save(school=self.request.school)


class TermViewSet(viewsets.ModelViewSet):
    """CRUD for Term."""

    serializer_class = TermSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.permission_classes = [IsAccountant]
        else:
            self.permission_classes = [IsBursar]
        return super().get_permissions()

    def get_queryset(self):
        school = getattr(self.request, "school", None)
        return Term.objects.for_school(school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.school)

    def perform_update(self, serializer):
        serializer.save(school=self.request.school)


class ClassStreamViewSet(viewsets.ModelViewSet):
    """CRUD for ClassStream."""

    serializer_class = ClassStreamSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.permission_classes = [IsAccountant]
        else:
            self.permission_classes = [IsBursar]
        return super().get_permissions()

    def get_queryset(self):
        school = getattr(self.request, "school", None)
        return ClassStream.objects.for_school(school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.school)

    def perform_update(self, serializer):
        serializer.save(school=self.request.school)

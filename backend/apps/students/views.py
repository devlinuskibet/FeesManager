"""Views for the students app.

All viewsets scope their querysets to request.school (TenantMiddleware) and set
school=self.request.school on create/update so records never leak across
tenants.
"""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from apps.accounts.permissions import IsAccountant, IsBursar

from . import import_service
from .models import Guardian, Student, StudentGuardian
from .serializers import (
    GuardianSerializer,
    StudentDetailSerializer,
    StudentGuardianSerializer,
    StudentSerializer,
)


class _SchoolScopedViewSet(ModelViewSet):
    """Base: scope queryset to request.school; force school on save."""

    def get_queryset(self):
        school = getattr(self.request, "school", None)
        qs = self.queryset
        if qs is not None:
            return qs.for_school(school)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(school=self.request.school)

    def perform_update(self, serializer):
        serializer.save(school=self.request.school)


class StudentViewSet(_SchoolScopedViewSet):
    """CRUD for Student."""

    queryset = Student.objects.all()
    serializer_class = StudentSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.permission_classes = [IsAccountant]
        else:
            self.permission_classes = [IsBursar]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return StudentDetailSerializer
        return StudentSerializer

    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        """Bulk import students (and guardians) from CSV or Excel.

        Request: multipart/form-data with 'file' and optional 'dry_run' (true/false).
        Returns a validation report. When dry_run=false and valid, commits
        atomically.
        """
        uploaded = request.FILES.get("file")
        dry_run = str(request.data.get("dry_run", "true")).lower() == "true"

        if not uploaded:
            return Response(
                {"error": "No file provided. Use form field 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        report = import_service.import_students(
            uploaded_file=uploaded,
            school=request.school,
            dry_run=dry_run,
            user=request.user,
        )
        status_code = status.HTTP_200_OK if dry_run or report["status"] == "ok" else status.HTTP_400_BAD_REQUEST
        return Response(report, status=status_code)


class GuardianViewSet(_SchoolScopedViewSet):
    """CRUD for Guardian."""

    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.permission_classes = [IsAccountant]
        else:
            self.permission_classes = [IsBursar]
        return super().get_permissions()


class StudentGuardianViewSet(_SchoolScopedViewSet):
    """CRUD for StudentGuardian links."""

    queryset = StudentGuardian.objects.all()
    serializer_class = StudentGuardianSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            self.permission_classes = [IsAccountant]
        else:
            self.permission_classes = [IsBursar]
        return super().get_permissions()

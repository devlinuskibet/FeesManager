"""URLs for the students app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"students", views.StudentViewSet, basename="student")
router.register(r"guardians", views.GuardianViewSet, basename="guardian")
router.register(r"guardian-links", views.StudentGuardianViewSet, basename="studentguardian")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "import/",
        views.StudentViewSet.as_view({"post": "import_csv"}),
        name="student-import",
    ),
]

"""URLs for the academics app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"academic-years", views.AcademicYearViewSet, basename="academicyear")
router.register(r"terms", views.TermViewSet, basename="term")
router.register(r"class-streams", views.ClassStreamViewSet, basename="classstream")

urlpatterns = [path("", include(router.urls))]

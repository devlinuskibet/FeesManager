"""URLs for the tenants app."""

from django.urls import path

from . import views

urlpatterns = [
    path("schools/", views.SchoolListCreateView.as_view(), name="school-list-create"),
]

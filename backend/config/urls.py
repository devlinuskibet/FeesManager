"""URL routing for the School Fee & Payment Tracker API."""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI schema and Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    # Authentication (JWT token obtain/refresh, current-user profile)
    path("api/v1/auth/", include("apps.accounts.urls")),
    # Tenant/school management
    path("api/v1/tenants/", include("apps.tenants.urls")),
    # Academic structure
    path("api/v1/academics/", include("apps.academics.urls")),
    # Students and guardians
    path("api/v1/students/", include("apps.students.urls")),
]

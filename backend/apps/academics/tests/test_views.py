"""Tests for academics CRUD APIs and cross-tenant isolation."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.tenants.models import School


@pytest.fixture
def api_client(school):
    client = APIClient()
    client.defaults["HTTP_X_School_ID"] = str(school.id)
    return client


@pytest.mark.django_db
def test_crud_academic_year(api_client, admin_user, school, bursar_user):
    client = api_client
    client.force_authenticate(user=admin_user)

    # Create
    resp = client.post(
        "/api/v1/academics/academic-years/",
        {
            "school": school.id,
            "name": "2027",
            "start_date": "2027-01-01",
            "end_date": "2027-12-31",
            "is_current": True,
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    ay_id = resp.json()["id"]

    # List — scoped to school
    resp = client.get("/api/v1/academics/academic-years/")
    assert resp.status_code == status.HTTP_200_OK
    results = resp.json()["results"] if "results" in resp.json() else resp.json()
    assert any(r["id"] == ay_id for r in results)

    # Retrieve
    resp = client.get(f"/api/v1/academics/academic-years/{ay_id}/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["name"] == "2027"

    # Update
    resp = client.patch(
        f"/api/v1/academics/academic-years/{ay_id}/",
        {"name": "2027-2028"},
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["name"] == "2027-2028"


@pytest.mark.django_db
def test_accountant_can_read_but_not_write(api_client, accountant_user, school):
    client = api_client
    client.force_authenticate(user=accountant_user)

    resp = client.get("/api/v1/academics/academic-years/")
    assert resp.status_code == status.HTTP_200_OK

    resp = client.post(
        "/api/v1/academics/academic-years/",
        {
            "school": school.id,
            "name": "2028",
            "start_date": "2028-01-01",
            "end_date": "2028-12-31",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cross_tenant_isolation(api_client, admin_user):
    """School A user cannot see or write School B's academic years."""
    client = api_client
    client.force_authenticate(user=admin_user)

    school_a = admin_user.memberships.first().school
    school_b = School.objects.create(name="Other School", slug="other-school", email="bursar@other.sc.ke")

    # Create a year in school B directly
    from apps.academics.models import AcademicYear

    AcademicYear.objects.create(
        school=school_b,
        name="2027",
        start_date="2027-01-01",
        end_date="2027-12-31",
    )

    # List for school A should not include school B's year
    resp = client.get("/api/v1/academics/academic-years/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    results = data["results"] if "results" in data else data
    assert all(r["school"] != school_b.id for r in results)

    # Try to write to school B explicitly
    resp = client.post(
        "/api/v1/academics/academic-years/",
        {
            "school": school_b.id,
            "name": "2028",
            "start_date": "2028-01-01",
            "end_date": "2028-12-31",
        },
        format="json",
    )
    # perform_create forces school=self.request.school, so school_b is ignored
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json()["school"] == school_a.id

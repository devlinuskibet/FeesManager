"""Tests for students CRUD APIs and cross-tenant isolation."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.academics.models import AcademicYear, ClassStream
from apps.tenants.models import School


@pytest.fixture
def api_client(school):
    client = APIClient()
    client.defaults["HTTP_X_School_ID"] = str(school.id)
    return client


@pytest.mark.django_db
def test_student_crud(api_client, admin_user, school, bursar_user):
    client = api_client
    client.force_authenticate(user=admin_user)

    ay = AcademicYear.objects.create(school=school, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    cs = ClassStream.objects.create(school=school, level="Form 1", stream="East", academic_year=ay)

    resp = client.post(
        "/api/v1/students/students/",
        {
            "school": school.id,
            "admission_number": "ADM001",
            "first_name": "John",
            "last_name": "Doe",
            "class_stream": cs.id,
            "status": "active",
            "date_admitted": "2027-01-10",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_201_CREATED, resp.content
    sid = resp.json()["id"]

    resp = client.get(f"/api/v1/students/students/{sid}/")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["admission_number"] == "ADM001"
    assert resp.json()["full_name"] == "John Doe"

    resp = client.get("/api/v1/students/students/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    results = data["results"] if "results" in data else data
    assert any(r["id"] == sid for r in results)


@pytest.mark.django_db
def test_accountant_read_only(api_client, accountant_user, school):
    client = api_client
    client.force_authenticate(user=accountant_user)

    resp = client.get("/api/v1/students/students/")
    assert resp.status_code == status.HTTP_200_OK

    resp = client.post(
        "/api/v1/students/students/",
        {
            "school": school.id,
            "admission_number": "ADM002",
            "first_name": "Jane",
            "last_name": "Doe",
            "class_stream": 1,
            "status": "active",
            "date_admitted": "2027-01-10",
        },
        format="json",
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_cross_tenant_isolation_students(api_client, admin_user, school):
    """School A user cannot see School B's students."""
    client = api_client
    client.force_authenticate(user=admin_user)

    school_b = School.objects.create(name="Other School", slug="other-school", email="bursar@other.sc.ke")
    ay_b = AcademicYear.objects.create(school=school_b, name="2027", start_date="2027-01-01", end_date="2027-12-31")
    cs_b = ClassStream.objects.create(school=school_b, level="Form 1", stream="East", academic_year=ay_b)
    from apps.students.models import Student

    Student.objects.create(
        school=school_b,
        admission_number="B-001",
        first_name="Other",
        last_name="Student",
        class_stream=cs_b,
        date_admitted="2027-01-10",
    )

    resp = client.get("/api/v1/students/students/")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    results = data["results"] if "results" in data else data
    assert all(r["school"] != school_b.id for r in results)

"""Tests for JWT authentication endpoints."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Role
from apps.tenants.models import School

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_obtain_token_returns_access_and_refresh(api_client):
    user = User.objects.create_user(
        username="b@example.com",
        email="b@example.com",
        password="strongPass123!",
    )
    school = School.objects.create(name="Token School", slug="token-school")
    role = Role.objects.create(name="school_admin", school=school)
    Membership.objects.create(user=user, school=school, role=role, is_active=True)

    resp = api_client.post(
        "/api/v1/auth/token/",
        {"email": "b@example.com", "password": "strongPass123!"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    data = resp.json()
    assert "access" in data
    assert "refresh" in data


@pytest.mark.django_db
def test_obtain_token_rejects_wrong_password(api_client):
    User.objects.create_user(
        username="b@example.com",
        email="b@example.com",
        password="strongPass123!",
    )
    resp = api_client.post(
        "/api/v1/auth/token/",
        {"email": "b@example.com", "password": "wrongPassword123!"},
        format="json",
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_me_endpoint_requires_auth(api_client):
    resp = api_client.get("/api/v1/auth/me/", format="json")
    assert resp.status_code == 401

    user = User.objects.create_user(
        username="m@example.com",
        email="m@example.com",
        password="strongPass123!",
    )
    api_client.force_authenticate(user=user)
    resp = api_client.get("/api/v1/auth/me/", format="json")
    assert resp.status_code == 200
    assert resp.json()["email"] == "m@example.com"

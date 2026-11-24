"""Tests for the School model and tenant scoping."""

import pytest
from django.db import IntegrityError

from apps.tenants.models import School


@pytest.mark.django_db
def test_school_creation_and_str():
    school = School.objects.create(
        name="Light Bridge Academy",
        slug="light-bridge-academy",
        email="bursar@lightbridge.sc.ke",
    )
    assert school.pk is not None
    assert str(school) == "Light Bridge Academy"
    assert school.slug == "light-bridge-academy"
    assert school.is_active is True


@pytest.mark.django_db
def test_slug_is_unique():
    School.objects.create(name="One", slug="uniq-school")
    with pytest.raises(IntegrityError):
        School.objects.create(name="Two", slug="uniq-school")

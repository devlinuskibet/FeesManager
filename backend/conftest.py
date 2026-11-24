"""Pytest fixtures shared across the test suite.

Requires the DJANGO_SETTINGS_MODULE env var (set in pyproject.toml as the
pytest ini option django_settings_module).
"""

import pytest
from apps.accounts.models import Membership, Role
from apps.tenants.models import School
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def school(db):
    """A default active school."""
    return School.objects.create(
        name="Demo School",
        slug="demo-school",
        email="bursar@demo.sc.ke",
        phone="+254700000000",
    )


@pytest.fixture
def admin_user(db, school):
    """A user with the school_admin role on the default school."""
    user = User.objects.create_user(
        username="admin@demo.sc.ke",
        email="admin@demo.sc.ke",
        password="AdminPass123!",
    )
    role = Role.objects.create(name="school_admin", school=school)
    Membership.objects.create(user=user, school=school, role=role, is_active=True)
    return user


@pytest.fixture
def bursar_user(db, school):
    """A user with the bursar role on the default school."""
    user = User.objects.create_user(
        username="bursar@demo.sc.ke",
        email="bursar@demo.sc.ke",
        password="BursarPass123!",
    )
    role = Role.objects.create(name="bursar", school=school)
    Membership.objects.create(user=user, school=school, role=role, is_active=True)
    return user


@pytest.fixture
def accountant_user(db, school):
    """A user with the accountant role on the default school."""
    user = User.objects.create_user(
        username="accountant@demo.sc.ke",
        email="accountant@demo.sc.ke",
        password="AcctPass123!",
    )
    role = Role.objects.create(name="accountant", school=school)
    Membership.objects.create(user=user, school=school, role=role, is_active=True)
    return user

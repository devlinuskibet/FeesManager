"""Tests for User, Role, and Membership models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.accounts.models import Membership, Role
from apps.tenants.models import School

User = get_user_model()


@pytest.mark.django_db
def test_create_user_normalizes_email_domain():
    # Django normalizes the domain part of the email to lowercase but
    # preserves the local part (case-sensitive).
    user = User.objects.create_user(
        username="Bursar@Example.Com",
        email="Bursar@Example.Com",
        password="strongPass123!",
    )
    assert user.pk is not None
    assert user.check_password("strongPass123!")
    assert user.email == "Bursar@example.com"
    # Username is stored as passed; only the email domain is normalized.
    assert user.username == "Bursar@Example.Com"
    assert user.full_name == "Bursar@example.com"


@pytest.mark.django_db
def test_create_user_without_password_sets_unusable_password():
    # create_user() accepts a missing password and marks it unusable
    # rather than raising TypeError.
    user = User.objects.create_user(username="nopass@example.com", email="nopass@example.com")
    assert user.pk is not None
    assert not user.has_usable_password()


@pytest.mark.django_db
def test_role_and_membership_link_user_to_school():
    school = School.objects.create(name="Test School", slug="test-school")
    user = User.objects.create_user(username="u@example.com", email="u@example.com", password="pass12345")
    role = Role.objects.create(name="bursar", school=school)
    membership = Membership.objects.create(user=user, school=school, role=role, is_active=True)
    assert user.memberships.filter(is_active=True).count() == 1
    assert membership.role_type == "bursar"
    assert str(membership) == "u@example.com @ test-school (bursar)"


@pytest.mark.django_db
def test_role_unique_per_school():
    school = School.objects.create(name="Uniq School", slug="uniq-school")
    Role.objects.create(name="bursar", school=school)
    with pytest.raises(IntegrityError):
        Role.objects.create(name="bursar", school=school)

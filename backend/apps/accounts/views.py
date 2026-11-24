"""Authentication and profile views for the accounts app."""

from rest_framework import generics, permissions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import (
    TokenObtainPairView,  # re-exported via urls
)

from .serializers import UserSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT obtain serializer that embeds useful claims in the access token.

    Claims added: email, full_name, schools (slugs), roles. The frontend can
    read these without an extra round trip.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["full_name"] = user.full_name
        memberships = user.memberships.filter(is_active=True).select_related("school", "role")
        token["schools"] = [m.school.slug for m in memberships]
        token["roles"] = [m.role.name for m in memberships]
        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    """POST /api/v1/auth/token/ — email + password -> access + refresh tokens."""

    serializer_class = CustomTokenObtainPairSerializer


class MeView(generics.RetrieveAPIView):
    """GET /api/v1/auth/me/ — the authenticated user's profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

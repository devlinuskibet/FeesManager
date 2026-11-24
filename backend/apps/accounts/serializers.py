"""Serializers for the accounts app."""

from rest_framework import serializers

from .models import Membership, User


class UserSerializer(serializers.ModelSerializer):
    """Public user profile representation."""

    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "is_verified",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined", "is_verified")

    def get_full_name(self, obj):
        return obj.full_name


class MembershipSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    school_slug = serializers.SlugField(source="school.slug", read_only=True)
    school_name = serializers.CharField(source="school.name", read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "school", "school_slug", "school_name", "role", "role_name", "is_active")
        read_only_fields = ("id",)

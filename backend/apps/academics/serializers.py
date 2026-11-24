"""Serializers for the academics app."""

from rest_framework import serializers

from .models import AcademicYear, ClassStream, Term


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = (
            "id",
            "school",
            "name",
            "start_date",
            "end_date",
            "is_current",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = (
            "id",
            "school",
            "academic_year",
            "name",
            "term_number",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ClassStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassStream
        fields = (
            "id",
            "school",
            "name",
            "level",
            "stream",
            "academic_year",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

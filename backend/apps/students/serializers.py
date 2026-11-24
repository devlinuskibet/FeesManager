"""Serializers for the students app."""

from rest_framework import serializers

from .models import Guardian, Student, StudentGuardian


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Student
        fields = (
            "id",
            "school",
            "admission_number",
            "first_name",
            "last_name",
            "full_name",
            "class_stream",
            "status",
            "date_admitted",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_full_name(self, obj):
        return obj.full_name

    def validate_admission_number(self, value):
        # Normalize before validation so duplicates are caught consistently.
        import re

        if value:
            value = re.sub(r"\s+", "", value.strip()).upper()
        return value


class GuardianSerializer(serializers.ModelSerializer):
    class Meta:
        model = Guardian
        fields = (
            "id",
            "school",
            "name",
            "phone",
            "relationship",
            "is_primary",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class StudentGuardianSerializer(serializers.ModelSerializer):
    student_admission_number = serializers.CharField(source="student.admission_number", read_only=True)
    guardian_name = serializers.CharField(source="guardian.name", read_only=True)
    guardian_phone = serializers.CharField(source="guardian.phone", read_only=True)

    class Meta:
        model = StudentGuardian
        fields = (
            "id",
            "school",
            "student",
            "student_admission_number",
            "guardian",
            "guardian_name",
            "guardian_phone",
            "is_primary",
            "relationship",
            "created_at",
        )
        read_only_fields = ("id", "created_at")


class StudentDetailSerializer(StudentSerializer):
    """Student with linked guardians (nested)."""

    guardian_links = StudentGuardianSerializer(many=True, read_only=True)

    class Meta(StudentSerializer.Meta):
        fields = StudentSerializer.Meta.fields + ("guardian_links",)

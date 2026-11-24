"""Admin registration for the students app."""

from django.contrib import admin

from .models import Guardian, Student, StudentGuardian


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("admission_number", "full_name", "school", "status", "class_stream")
    list_filter = ("status", "school", "class_stream")
    search_fields = ("admission_number", "first_name", "last_name")


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "school", "relationship", "is_primary")
    list_filter = ("relationship", "is_primary", "school")
    search_fields = ("name", "phone")


@admin.register(StudentGuardian)
class StudentGuardianAdmin(admin.ModelAdmin):
    list_display = ("student", "guardian", "school", "is_primary")
    list_filter = ("is_primary", "school")
    search_fields = ("student__admission_number", "guardian__name")

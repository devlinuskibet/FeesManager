"""Admin registration for the academics app."""

from django.contrib import admin

from .models import AcademicYear, ClassStream, Term


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "start_date", "end_date", "is_current")
    list_filter = ("is_current", "school")
    search_fields = ("name", "school__name")


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "term_number", "academic_year", "school", "is_active")
    list_filter = ("is_active", "name", "school")
    search_fields = ("name", "academic_year__name", "school__name")


@admin.register(ClassStream)
class ClassStreamAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "stream", "school", "is_active")
    list_filter = ("is_active", "school")
    search_fields = ("name", "level", "school__name")

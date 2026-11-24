"""Admin registration for the accounts app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Membership, Role, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "username", "full_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "username")
    ordering = ("email",)
    fieldsets = UserAdmin.fieldsets + (("Contact", {"fields": ("phone", "is_verified")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Contact", {"fields": ("phone",)}),)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "school")
    list_filter = ("name", "school")
    search_fields = ("name", "school__name")


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "school", "role", "is_active", "created_at")
    list_filter = ("is_active", "role__name", "school")
    search_fields = ("user__email", "school__name")

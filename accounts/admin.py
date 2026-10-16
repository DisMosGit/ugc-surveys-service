from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.http import HttpRequest

from accounts.models import AdminUser, ApiUser


@admin.register(AdminUser)
class AdminUserAdmin(BaseUserAdmin):
    list_display = ("username", "is_staff", "is_active", "created_at")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email")
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("id", "username", "password")}),
        ("Персональная информация", {"fields": ("first_name", "last_name", "email")}),
        (
            "Права доступа",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Важные даты", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )


@admin.register(ApiUser)
class ApiUserAdmin(admin.ModelAdmin):
    list_display = ("unsafe_id", "id", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("unsafe_id",)
    readonly_fields = ("id", "unsafe_id", "created_at", "updated_at")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

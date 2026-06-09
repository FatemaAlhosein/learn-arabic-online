"""
accounts/admin.py

Register our custom User and the three profile models in Django admin.

We subclass DjangoUserAdmin (the default admin for auth.User) and override
its forms + fieldsets, because the originals reference the `username` field
that we dropped from our model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import ParentProfile, StudentProfile, TeacherProfile, User


# =========================================================
# Custom forms — replace 'username' with 'email'
# =========================================================
class UserAdminCreationForm(UserCreationForm):
    """Form used when adding a new user in admin."""

    class Meta(UserCreationForm.Meta):
        model = User
        # email is the login identifier; role decides which profile is auto-made.
        fields = ("email", "role")


class UserAdminChangeForm(UserChangeForm):
    """Form used when editing an existing user in admin."""

    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


# =========================================================
# User admin
# =========================================================
@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    ordering = ("-date_joined",)
    list_display = ("email", "role", "first_name", "last_name",
                    "is_active", "is_staff", "date_joined")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "first_name", "last_name")

    # Layout of the EDIT form (existing user).
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name")}),
        (_("Role & permissions"), {
            "fields": ("role", "is_active", "is_staff", "is_superuser",
                       "groups", "user_permissions"),
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    # Layout of the ADD form (new user). Password fields are auto-handled
    # by UserCreationForm (password1 + password2).
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "role", "password1", "password2"),
        }),
    )


# =========================================================
# Profile admins
# =========================================================
@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "specialization", "years_of_experience",
                    "is_approved", "created_at")
    list_filter = ("is_approved",)
    search_fields = ("user__email", "specialization")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "age_track", "date_of_birth", "native_language",
                    "parent", "created_at")
    list_filter = ("age_track",)
    search_fields = ("user__email", "native_language")
    autocomplete_fields = ("user", "parent")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ParentProfile)
class ParentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "created_at")
    search_fields = ("user__email", "phone")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")

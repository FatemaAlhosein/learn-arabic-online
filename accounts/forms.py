"""
accounts/forms.py

Public-facing forms (signup). The admin-side User forms live in
accounts/admin.py because they extend Django's UserCreationForm /
UserChangeForm with extra admin-only fields.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import ParentProfile, StudentProfile, TeacherProfile, User


class SignupForm(UserCreationForm):
    """
    Public signup. Always creates a User.

    The role choices are limited to student / parent — admins and teachers
    are created by an existing admin in the Django admin, never via public
    signup.

    age_track is asked only when role=student. We collect it on the form
    and apply it to the auto-created StudentProfile in save().
    """

    PUBLIC_ROLES = (
        (User.Role.STUDENT, "Student — I want to learn Arabic"),
        (User.Role.PARENT,  "Parent — I'm signing up to manage my child's account"),
    )

    role = forms.ChoiceField(
        choices=PUBLIC_ROLES,
        widget=forms.RadioSelect,
        initial=User.Role.STUDENT,
        label="I am a...",
    )
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)

    # Asked for student signups (validated server-side; ignored for parents).
    age_track = forms.ChoiceField(
        choices=StudentProfile.AgeTrack.choices,
        required=False,
        initial=StudentProfile.AgeTrack.ADULT,
        label="Age group",
        help_text="Determines the style of content (kids / teen / adult).",
    )

    class Meta:
        model = User
        # No 'username' — our model dropped it.
        fields = ("email", "first_name", "last_name", "role")

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        age_track = cleaned.get("age_track")
        if role == User.Role.STUDENT and not age_track:
            self.add_error("age_track", "Please choose an age group.")
        return cleaned

    def save(self, commit=True):
        # Save the user first — the post_save signal in accounts/signals.py
        # auto-creates the matching profile based on user.role.
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save()
            # If student, push the chosen age_track onto the auto-created profile.
            if user.role == User.Role.STUDENT:
                profile = user.student_profile
                profile.age_track = self.cleaned_data["age_track"]
                profile.save(update_fields=["age_track"])
        return user


# =========================================================
# Profile edit forms (for the /accounts/profile/ page)
# =========================================================
class UserBasicForm(forms.ModelForm):
    """Edit first_name / last_name on the User model."""

    class Meta:
        model = User
        fields = ["first_name", "last_name"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
        }


class StudentProfileForm(forms.ModelForm):
    """
    Edit the StudentProfile fields a student can change themselves.

    age_track is intentionally excluded — students cannot change it manually.
    It is auto-computed from date_of_birth in save(), and can only be
    overridden by an admin or parent.
    """

    class Meta:
        model = StudentProfile
        fields = ["avatar", "native_language", "date_of_birth"]
        widgets = {
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "native_language": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. English, French…",
            }),
            "date_of_birth": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
        }
        labels = {
            "native_language": "Native language",
            "date_of_birth": "Date of birth",
        }

    def save(self, commit=True):
        """Auto-compute age_track from date_of_birth whenever it is set."""
        profile = super().save(commit=False)
        dob = self.cleaned_data.get("date_of_birth")
        if dob:
            from datetime import date
            today = date.today()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
            if age < 12:
                profile.age_track = StudentProfile.AgeTrack.KIDS
            elif age < 18:
                profile.age_track = StudentProfile.AgeTrack.TEEN
            else:
                profile.age_track = StudentProfile.AgeTrack.ADULT
        if commit:
            profile.save()
        return profile


class TeacherProfileForm(forms.ModelForm):
    """Edit the TeacherProfile fields a teacher can change themselves."""

    class Meta:
        model = TeacherProfile
        fields = ["avatar", "bio", "specialization", "years_of_experience"]
        widgets = {
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"class": "form-control", "rows": 4,
                                         "placeholder": "A short bio visible to students…"}),
            "specialization": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Modern Standard Arabic, Classical Arabic…",
            }),
            "years_of_experience": forms.NumberInput(attrs={
                "class": "form-control", "min": 0,
            }),
        }


class ParentProfileForm(forms.ModelForm):
    """Edit the ParentProfile fields a parent can change themselves."""

    class Meta:
        model = ParentProfile
        fields = ["avatar", "phone"]
        widgets = {
            "avatar": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "+1 555 000 0000",
            }),
        }


class LinkChildForm(forms.Form):
    """Form for a parent to link a student account by email."""

    child_email = forms.EmailField(
        label="Child's account email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "child@example.com",
        }),
    )

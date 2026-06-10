"""
accounts/views.py

Public auth views.

  GET/POST  /accounts/signup/          -> SignupView
  GET/POST  /accounts/profile/         -> profile_view  (edit own profile)
  POST      /accounts/link-child/      -> link_child    (parent only)
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import (
    LinkChildForm,
    ParentProfileForm,
    SignupForm,
    StudentProfileForm,
    TeacherProfileForm,
    UserBasicForm,
)
from .models import StudentProfile, User


class SignupView(CreateView):
    """
    Public signup page — currently disabled during beta.
    Redirects visitors to the demo instead.
    """

    model = User
    form_class = SignupForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        # Registration is closed during beta — redirect to demo
        messages.info(
            request,
            "🚧 Registration is currently closed while we finish building. "
            "Try the demo to explore all features!"
        )
        return redirect("accounts:demo_login")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


# =========================================================
# Profile — /accounts/profile/
# =========================================================
@login_required
def profile_view(request):
    """
    Let any authenticated user edit their own profile.
    Renders a two-form page: UserBasicForm (name) + role-specific profile form.
    """
    user = request.user

    # Pick the role-specific profile form and instance.
    role = user.role
    profile_instance = None
    profile_form_class = None

    if role == User.Role.STUDENT:
        profile_instance = getattr(user, "student_profile", None)
        profile_form_class = StudentProfileForm
    elif role == User.Role.TEACHER:
        profile_instance = getattr(user, "teacher_profile", None)
        profile_form_class = TeacherProfileForm
    elif role == User.Role.PARENT:
        profile_instance = getattr(user, "parent_profile", None)
        profile_form_class = ParentProfileForm

    if request.method == "POST":
        user_form = UserBasicForm(request.POST, instance=user)
        profile_form = (
            profile_form_class(request.POST, request.FILES, instance=profile_instance)
            if profile_form_class else None
        )

        user_valid = user_form.is_valid()
        profile_valid = profile_form.is_valid() if profile_form else True

        if user_valid and profile_valid:
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        user_form = UserBasicForm(instance=user)
        profile_form = (
            profile_form_class(instance=profile_instance)
            if profile_form_class else None
        )

    # For students: pull current level + placement quiz link
    placement_quiz = None
    if role == User.Role.STUDENT:
        from assessments.models import Quiz
        placement_quiz = (
            Quiz.objects.filter(kind=Quiz.Kind.PLACEMENT, is_published=True)
            .order_by("-created_at")
            .first()
        )

    return render(request, "registration/profile.html", {
        "user_form": user_form,
        "profile_form": profile_form,
        "profile_instance": profile_instance,
        "placement_quiz": placement_quiz,
    })


# =========================================================
# Link child — POST /accounts/link-child/   (parents only)
# =========================================================
@login_required
def link_child(request):
    """
    Let a parent link a student account to their profile by email.
    The student must already have an account with role=student.
    """
    if not request.user.is_parent:
        messages.error(request, "Only parent accounts can link children.")
        return redirect("dashboard")

    parent_profile = getattr(request.user, "parent_profile", None)
    if parent_profile is None:
        messages.error(request, "Parent profile missing — contact support.")
        return redirect("dashboard")

    if request.method == "POST":
        form = LinkChildForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["child_email"].strip().lower()
            try:
                child_user = User.objects.get(email__iexact=email, role=User.Role.STUDENT)
                child_profile = child_user.student_profile
            except User.DoesNotExist:
                messages.error(
                    request,
                    "No student account found with that email. "
                    "Make sure the child has already signed up.",
                )
                return redirect("dashboard")

            if child_profile.parent == parent_profile:
                messages.info(request, "That student is already linked to your account.")
            elif child_profile.parent is not None:
                messages.warning(
                    request,
                    "That student account is already linked to another parent. "
                    "Contact support if you believe this is an error.",
                )
            else:
                child_profile.parent = parent_profile
                child_profile.save(update_fields=["parent"])
                messages.success(
                    request,
                    f"{child_user.first_name or email} has been linked to your account.",
                )
    else:
        messages.error(request, "Invalid request.")

    return redirect("dashboard")


def demo_login(request):
    """Auto-login as the demo student account so visitors can explore the site."""
    from django.contrib.auth import authenticate, login as auth_login
    DEMO_EMAIL    = "demo@learnarabicasl.com"
    DEMO_PASSWORD = "Demo1234!"
    user = authenticate(request, username=DEMO_EMAIL, password=DEMO_PASSWORD)
    if user is not None:
        auth_login(request, user)
        messages.info(request, "You're browsing as a demo student. Create a free account to save your progress!")
        return redirect("dashboard")
    messages.warning(request, "Demo account not available yet. Please sign up for free!")
    return redirect("accounts:signup")

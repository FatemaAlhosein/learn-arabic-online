"""
accounts/models.py

Custom User model + role-specific profile models for Bayt al-Hikma:
  - email is the login identifier (no username)
  - every user has a `role`: admin / teacher / student / parent
  - on User creation, the matching profile is auto-created via a
    post_save signal (see accounts/signals.py)
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


# =========================================================
# Manager — handles user creation when there is no username
# =========================================================
class UserManager(BaseUserManager):
    """
    Replaces the default UserManager so create_user() / create_superuser()
    accept `email` instead of `username`.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)        # hashes the password
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


# =========================================================
# User model
# =========================================================
class User(AbstractUser):
    """
    Bayt al-Hikma user:
      - logs in by email
      - has one role (admin/teacher/student/parent) which determines
        which profile gets auto-created (Phase 3C)
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"
        PARENT = "parent", "Parent"

    # Disable the inherited username field — we use email instead.
    username = None

    # Email must be unique (the inherited one isn't).
    email = models.EmailField("email address", unique=True)

    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Determines which profile is auto-created and what the user can do.",
    )

    # Tell Django that `email` is the login field.
    USERNAME_FIELD = "email"

    # Fields prompted for when running `createsuperuser`, in addition to
    # USERNAME_FIELD and password. Empty list means: just email + password.
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    # --- Convenience role checks (handy in templates and views) ---
    @property
    def is_teacher(self) -> bool:
        return self.role == self.Role.TEACHER

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT

    @property
    def is_parent(self) -> bool:
        return self.role == self.Role.PARENT

    @property
    def is_admin_role(self) -> bool:
        # Note: separate from `is_staff` / `is_superuser`, which control
        # admin-panel access. This checks the *business* role.
        return self.role == self.Role.ADMIN


# =========================================================
# Profile models — one row per non-admin user
# =========================================================
class TeacherProfile(models.Model):
    """Extra fields for users with role=teacher."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    bio = models.TextField(blank=True)
    specialization = models.CharField(max_length=120, blank=True)
    years_of_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    avatar = models.ImageField(
        upload_to="avatars/teachers/",
        null=True,
        blank=True,
    )
    # Admin-only flag: until approved, teacher cannot publish courses.
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "teacher profile"
        verbose_name_plural = "teacher profiles"

    def __str__(self):
        return f"Teacher: {self.user.email}"


class ParentProfile(models.Model):
    """Extra fields for users with role=parent. Parents may manage child students."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_profile",
    )
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(
        upload_to="avatars/parents/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "parent profile"
        verbose_name_plural = "parent profiles"

    def __str__(self):
        return f"Parent: {self.user.email}"


class StudentProfile(models.Model):
    """
    Extra fields for users with role=student.

    `age_track` decides the *style of content* (kids = picture-heavy / playful,
    adult = dense / formal). It is independent of the level system —
    levels (A1 → C2) gate progression for any age, age_track only changes
    presentation.

    `current_level` (FK to curriculum.Level) is added in Phase 4 once that
    app exists. It will be a CACHED value, written when a certificate is
    earned, a placement test is passed, or an admin overrides it.
    """

    class AgeTrack(models.TextChoices):
        KIDS = "kids", "Kids (under 12)"
        TEEN = "teen", "Teen (12–17)"
        ADULT = "adult", "Adult (18+)"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    age_track = models.CharField(
        max_length=8,
        choices=AgeTrack.choices,
        default=AgeTrack.ADULT,
    )
    native_language = models.CharField(max_length=64, blank=True)
    avatar = models.ImageField(
        upload_to="avatars/students/",
        null=True,
        blank=True,
    )

    # Optional link to a parent (only used for kids enrolled by a guardian).
    parent = models.ForeignKey(
        "ParentProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    # CACHED proficiency level. Set by:
    #   - placement test result (Phase 7)
    #   - course-completion certificate (Phase 6)
    #   - admin override (any time)
    # Nullable on signup — new students have no level until they take placement
    # or admin assigns one. SET_NULL on level deletion (very rare; see Level
    # docstring) so we never lose the student row over a reference-table edit.
    current_level = models.ForeignKey(
        "curriculum.Level",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students_at_level",
        help_text="Cached current proficiency. Updated by placement / certificates / admin.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "student profile"
        verbose_name_plural = "student profiles"

    def __str__(self):
        return f"Student: {self.user.email}"

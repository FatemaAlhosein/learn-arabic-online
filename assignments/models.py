"""
assignments/models.py

Two tables:

  Assignment         — the task a teacher sets (attached to a lesson or course)
  AssignmentSubmission — a student's response + teacher's grade
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Assignment(models.Model):
    """
    A piece of work set by a teacher. Can be attached to a specific lesson
    OR to the course as a whole (not both). Lesson-level assignments appear
    inside the lesson player; course-level ones on the course detail page.
    """

    # Scope — at most one of these is set.
    lesson = models.ForeignKey(
        "curriculum.Lesson",
        on_delete=models.CASCADE,
        related_name="assignments",
        null=True,
        blank=True,
    )
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="assignments",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        help_text="Brief overview shown in the lesson/course page.",
    )
    instructions = models.TextField(
        help_text="Full instructions for the student. Markdown supported.",
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional deadline. Students can still submit after this.",
    )
    max_score = models.PositiveSmallIntegerField(
        default=100,
        help_text="Maximum possible score (used to calculate percentage).",
    )
    allow_file_upload = models.BooleanField(
        default=True,
        help_text="Students may attach a file (PDF, Word, image, etc.).",
    )
    allow_text_response = models.BooleanField(
        default=True,
        help_text="Students may type a written response.",
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Unpublished assignments are hidden from students.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assignments_created",
        limit_choices_to={"role": "teacher"},
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "assignment"
        verbose_name_plural = "assignments"

    def __str__(self):
        scope = self.lesson or self.course
        return f"{self.title} ({scope})"

    def clean(self):
        if self.lesson_id and self.course_id:
            raise ValidationError(
                "An assignment cannot belong to both a lesson and a course."
            )
        if not self.lesson_id and not self.course_id:
            raise ValidationError(
                "An assignment must belong to a lesson or a course."
            )
        if not self.allow_file_upload and not self.allow_text_response:
            raise ValidationError(
                "At least one of file upload or text response must be allowed."
            )

    @property
    def scope_course(self):
        """Return the parent Course regardless of whether scoped to lesson or course."""
        if self.lesson_id:
            return self.lesson.course
        return self.course


class AssignmentSubmission(models.Model):
    """
    One student's response to one assignment.
    One row per (student, assignment) — re-submissions overwrite the row.
    """

    class Status(models.TextChoices):
        PENDING  = "pending",  "Not submitted"
        SUBMITTED = "submitted", "Submitted — awaiting grade"
        GRADED   = "graded",   "Graded"

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
    )

    # Student's response.
    text_response = models.TextField(blank=True)
    file = models.FileField(
        upload_to="assignment_submissions/",
        blank=True,
        null=True,
        help_text="Uploaded file (PDF, Word, image, etc.).",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Teacher's grade.
    score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Points awarded (0 – assignment.max_score).",
    )
    feedback = models.TextField(
        blank=True,
        help_text="Teacher's written feedback, shown to the student.",
    )
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="graded_submissions",
    )

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "student"],
                name="submission_unique_assignment_student",
            ),
        ]
        verbose_name = "assignment submission"
        verbose_name_plural = "assignment submissions"

    def __str__(self):
        return f"{self.student} → {self.assignment.title} ({self.status})"

    @property
    def score_percent(self):
        """Return score as a percentage of max_score, or None."""
        if self.score is None:
            return None
        max_s = self.assignment.max_score or 100
        return int(round(100 * self.score / max_s))

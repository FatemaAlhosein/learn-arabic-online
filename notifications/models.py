"""
notifications/models.py

A simple in-app notification system.

Each Notification is addressed to one user (recipient). It holds a
short message, an optional click-through link, and an is_read flag.

Notification types (kind field) are intentionally coarse-grained so they
can drive icons and colour-coding without extra string matching in templates.
"""

from django.conf import settings
from django.db import models


class Notification(models.Model):

    class Kind(models.TextChoices):
        # Student-facing
        ENROLLMENT      = "enrollment",       "Enrolled in a course"
        COURSE_DONE     = "course_done",      "Course completed"
        ASSIGNMENT_GRADED = "assignment_graded", "Assignment graded"
        QUIZ_RESULT     = "quiz_result",      "Quiz result"
        # Teacher-facing
        ASSIGNMENT_SUBMITTED = "assignment_submitted", "Assignment submitted"
        NEW_ENROLLMENT  = "new_enrollment",   "New student enrolled"
        # Parent-facing
        CHILD_COURSE_DONE = "child_course_done", "Child completed a course"
        # Generic / system
        INFO            = "info",             "Info"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(
        max_length=30,
        choices=Kind.choices,
        default=Kind.INFO,
    )
    message = models.CharField(max_length=300)
    link = models.CharField(
        max_length=300,
        blank=True,
        help_text="Optional internal URL the notification points to.",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "notification"
        verbose_name_plural = "notifications"

    def __str__(self):
        return f"→ {self.recipient.email} [{self.kind}] {self.message[:60]}"

    # Convenience helper used in templates
    @property
    def icon(self):
        icons = {
            self.Kind.ENROLLMENT:           "bi-book",
            self.Kind.COURSE_DONE:          "bi-award",
            self.Kind.ASSIGNMENT_GRADED:    "bi-check2-circle",
            self.Kind.QUIZ_RESULT:          "bi-clipboard-check",
            self.Kind.ASSIGNMENT_SUBMITTED: "bi-file-earmark-text",
            self.Kind.NEW_ENROLLMENT:       "bi-person-plus",
            self.Kind.CHILD_COURSE_DONE:    "bi-award-fill",
            self.Kind.INFO:                 "bi-info-circle",
        }
        return icons.get(self.kind, "bi-bell")

    @property
    def colour_class(self):
        success = {
            self.Kind.COURSE_DONE, self.Kind.ASSIGNMENT_GRADED,
            self.Kind.CHILD_COURSE_DONE,
        }
        info = {
            self.Kind.ENROLLMENT, self.Kind.NEW_ENROLLMENT,
            self.Kind.QUIZ_RESULT, self.Kind.INFO,
        }
        if self.kind in success:
            return "text-bg-success"
        if self.kind in info:
            return "text-bg-primary"
        return "text-bg-secondary"

"""
agenda/models.py

Three models:

  ClassSchedule   — recurring weekly class times for a course
  AgendaItem      — a single event/task/note a teacher posts (homework, lesson note, event, reminder)
  StudentTask     — tracks whether a student has checked off an AgendaItem
"""

from django.conf import settings
from django.db import models


class ClassSchedule(models.Model):
    """Recurring weekly timetable entry for a course."""

    class Day(models.IntegerChoices):
        MONDAY    = 0, "Monday"
        TUESDAY   = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY  = 3, "Thursday"
        FRIDAY    = 4, "Friday"
        SATURDAY  = 5, "Saturday"
        SUNDAY    = 6, "Sunday"

    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="schedule_entries",
    )
    day_of_week = models.IntegerField(choices=Day.choices)
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    location    = models.CharField(
        max_length=200, blank=True,
        help_text="Room, Zoom link, or 'Online'.",
    )
    note        = models.CharField(max_length=300, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="schedule_entries_created",
    )

    class Meta:
        ordering = ["day_of_week", "start_time"]
        verbose_name = "class schedule entry"
        verbose_name_plural = "class schedule entries"

    def __str__(self):
        return f"{self.course} — {self.get_day_of_week_display()} {self.start_time:%H:%M}"


class AgendaItem(models.Model):
    """A single agenda entry posted by a teacher for a course."""

    class Kind(models.TextChoices):
        LESSON   = "lesson",   "📘 Lesson"
        HOMEWORK = "homework", "📝 Homework"
        QUIZ     = "quiz",     "❓ Quiz"
        EVENT    = "event",    "🎉 Event"
        REMINDER = "reminder", "🔔 Reminder"
        NOTE     = "note",     "💬 Note"

    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="agenda_items",
    )
    title       = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    kind        = models.CharField(max_length=12, choices=Kind.choices, default=Kind.NOTE)
    date        = models.DateField(help_text="The date this item is relevant to.")
    due_time    = models.TimeField(null=True, blank=True, help_text="Optional time (e.g. homework due 23:59).")
    is_done_default = models.BooleanField(
        default=False,
        help_text="Mark all student tasks as done automatically (e.g. for past lessons).",
    )

    # Optional link to an existing assignment or lesson.
    linked_assignment = models.ForeignKey(
        "assignments.Assignment",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="agenda_items",
    )
    linked_lesson = models.ForeignKey(
        "curriculum.Lesson",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="agenda_items",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="agenda_items_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "due_time", "kind"]
        verbose_name = "agenda item"
        verbose_name_plural = "agenda items"

    def __str__(self):
        return f"[{self.get_kind_display()}] {self.title} — {self.date}"


class StudentTask(models.Model):
    """Tracks whether a student has completed an AgendaItem."""

    agenda_item = models.ForeignKey(
        AgendaItem,
        on_delete=models.CASCADE,
        related_name="student_tasks",
    )
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="agenda_tasks",
    )
    is_done   = models.BooleanField(default=False)
    done_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["agenda_item", "student"],
                name="unique_student_task",
            )
        ]
        verbose_name = "student task"
        verbose_name_plural = "student tasks"

    def __str__(self):
        status = "✓" if self.is_done else "○"
        return f"{status} {self.student} — {self.agenda_item.title}"

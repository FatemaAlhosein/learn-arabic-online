# Generated manually — matches assignments/models.py exactly.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_studentprofile_current_level"),
        ("curriculum", "0004_lesson_video_file_alter_lesson_primary_video_url"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Assignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "lesson",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="curriculum.lesson",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="curriculum.course",
                    ),
                ),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, help_text="Brief overview shown in the lesson/course page.")),
                ("instructions", models.TextField(help_text="Full instructions for the student. Markdown supported.")),
                ("due_date", models.DateTimeField(blank=True, help_text="Optional deadline. Students can still submit after this.", null=True)),
                ("max_score", models.PositiveSmallIntegerField(default=100, help_text="Maximum possible score (used to calculate percentage).")),
                ("allow_file_upload", models.BooleanField(default=True, help_text="Students may attach a file (PDF, Word, image, etc.).")),
                ("allow_text_response", models.BooleanField(default=True, help_text="Students may type a written response.")),
                ("is_published", models.BooleanField(default=False, help_text="Unpublished assignments are hidden from students.")),
                (
                    "created_by",
                    models.ForeignKey(
                        limit_choices_to={"role": "teacher"},
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assignments_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "assignment",
                "verbose_name_plural": "assignments",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AssignmentSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="assignments.assignment",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_submissions",
                        to="accounts.studentprofile",
                    ),
                ),
                ("text_response", models.TextField(blank=True)),
                (
                    "file",
                    models.FileField(
                        blank=True,
                        help_text="Uploaded file (PDF, Word, image, etc.).",
                        null=True,
                        upload_to="assignment_submissions/",
                    ),
                ),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Not submitted"),
                            ("submitted", "Submitted — awaiting grade"),
                            ("graded", "Graded"),
                        ],
                        default="pending",
                        max_length=12,
                    ),
                ),
                ("score", models.PositiveSmallIntegerField(blank=True, help_text="Points awarded (0 – assignment.max_score).", null=True)),
                ("feedback", models.TextField(blank=True, help_text="Teacher's written feedback, shown to the student.")),
                ("graded_at", models.DateTimeField(blank=True, null=True)),
                (
                    "graded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="graded_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "assignment submission",
                "verbose_name_plural": "assignment submissions",
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="assignmentsubmission",
            constraint=models.UniqueConstraint(
                fields=["assignment", "student"],
                name="submission_unique_assignment_student",
            ),
        ),
    ]

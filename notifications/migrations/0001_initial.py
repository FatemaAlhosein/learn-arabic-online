from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("enrollment", "Enrolled in a course"),
                            ("course_done", "Course completed"),
                            ("assignment_graded", "Assignment graded"),
                            ("quiz_result", "Quiz result"),
                            ("assignment_submitted", "Assignment submitted"),
                            ("new_enrollment", "New student enrolled"),
                            ("child_course_done", "Child completed a course"),
                            ("info", "Info"),
                        ],
                        default="info",
                        max_length=30,
                    ),
                ),
                ("message", models.CharField(max_length=300)),
                ("link", models.CharField(blank=True, help_text="Optional internal URL the notification points to.", max_length=300)),
                ("is_read", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "verbose_name": "notification",
                "verbose_name_plural": "notifications",
                "ordering": ["-created_at"],
            },
        ),
    ]

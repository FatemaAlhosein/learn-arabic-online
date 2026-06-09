from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0002_studentprofile_current_level"),
        ("assignments", "0001_initial"),
        ("curriculum", "0004_lesson_video_file_alter_lesson_primary_video_url"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClassSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("day_of_week", models.IntegerField(choices=[(0,"Monday"),(1,"Tuesday"),(2,"Wednesday"),(3,"Thursday"),(4,"Friday"),(5,"Saturday"),(6,"Sunday")])),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("location", models.CharField(blank=True, max_length=200)),
                ("note", models.CharField(blank=True, max_length=300)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedule_entries", to="curriculum.course")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="schedule_entries_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["day_of_week", "start_time"], "verbose_name": "class schedule entry"},
        ),
        migrations.CreateModel(
            name="AgendaItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=300)),
                ("description", models.TextField(blank=True)),
                ("kind", models.CharField(choices=[("lesson","📘 Lesson"),("homework","📝 Homework"),("quiz","❓ Quiz"),("event","🎉 Event"),("reminder","🔔 Reminder"),("note","💬 Note")], default="note", max_length=12)),
                ("date", models.DateField()),
                ("due_time", models.TimeField(blank=True, null=True)),
                ("is_done_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agenda_items", to="curriculum.course")),
                ("linked_assignment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agenda_items", to="assignments.assignment")),
                ("linked_lesson", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agenda_items", to="curriculum.lesson")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agenda_items_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["date", "due_time", "kind"], "verbose_name": "agenda item"},
        ),
        migrations.CreateModel(
            name="StudentTask",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_done", models.BooleanField(default=False)),
                ("done_at", models.DateTimeField(blank=True, null=True)),
                ("agenda_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="student_tasks", to="agenda.agendaitem")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agenda_tasks", to="accounts.studentprofile")),
            ],
            options={"verbose_name": "student task"},
        ),
        migrations.AddConstraint(
            model_name="studenttask",
            constraint=models.UniqueConstraint(fields=["agenda_item", "student"], name="unique_student_task"),
        ),
    ]

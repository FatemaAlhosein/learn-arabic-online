"""
Data migration: seed the six CEFR levels (A1 → C2).

Idempotent — uses get_or_create() so re-running on an existing DB is safe.
The reverse direction wipes only these six rows (by code), so unrelated
level rows admins added later are left alone.
"""

from django.db import migrations


LEVELS = [
    ("A1", "Beginner 1",  1, "First contact with Arabic. Letters, sounds, "
                              "greetings, numbers."),
    ("A2", "Beginner 2",  2, "Familiar daily expressions and basic phrases."),
    ("B1", "Intermediate 1", 3, "Can deal with most situations encountered "
                                 "while travelling in an Arabic-speaking area."),
    ("B2", "Intermediate 2", 4, "Can interact with a degree of fluency and "
                                 "spontaneity. Reads articles and reports."),
    ("C1", "Advanced 1",  5, "Can express ideas fluently. Uses language "
                              "flexibly for social, academic and professional "
                              "purposes."),
    ("C2", "Advanced 2",  6, "Near-native command. Can summarise complex "
                              "spoken or written sources."),
]


def seed_levels(apps, schema_editor):
    Level = apps.get_model("curriculum", "Level")
    for code, name, order, description in LEVELS:
        Level.objects.get_or_create(
            code=code,
            defaults={"name": name, "order": order, "description": description},
        )


def unseed_levels(apps, schema_editor):
    Level = apps.get_model("curriculum", "Level")
    Level.objects.filter(code__in=[c for c, *_ in LEVELS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_levels, reverse_code=unseed_levels),
    ]

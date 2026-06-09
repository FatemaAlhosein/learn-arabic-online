from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("curriculum", "0004_lesson_video_file_alter_lesson_primary_video_url"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── VocabWord ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name="VocabWord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("arabic",        models.CharField(max_length=100, help_text="Full Arabic word with tashkeel, e.g. كِتَاب")),
                ("english",       models.CharField(max_length=120, help_text="English translation, e.g. Book")),
                ("emoji",         models.CharField(blank=True, max_length=10, help_text="Optional emoji, e.g. 📚")),
                ("phonetic",      models.CharField(blank=True, max_length=120, help_text="Romanised pronunciation, e.g. kitāb")),
                ("letters",       models.JSONField(blank=True, default=list, help_text='Individual letter tiles, e.g. ["ك","ت","ا","ب"]')),
                ("context_forms", models.JSONField(blank=True, default=list, help_text='Contextual shapes for Word Builder, e.g. ["كـ","ـتـ","ـا","ب"]')),
                ("missing_index", models.PositiveSmallIntegerField(blank=True, null=True, help_text="0-based index of the missing letter")),
                ("wrong_choices", models.JSONField(blank=True, default=list, help_text='2 wrong letter choices')),
                ("is_active",     models.BooleanField(default=True, help_text="Uncheck to hide from games")),
                ("created_at",    models.DateTimeField(auto_now_add=True)),
                ("updated_at",    models.DateTimeField(auto_now=True)),
                ("level", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="vocab_words",
                    to="curriculum.level",
                    help_text="CEFR level this word belongs to",
                )),
                ("course", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="vocab_words",
                    to="curriculum.course",
                    help_text="Optional: pin this word to a specific course",
                )),
                ("created_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="vocab_words_created",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "vocabulary word",
                "verbose_name_plural": "vocabulary words",
                "ordering": ["level__order", "english"],
            },
        ),

        # ── GameQuestion ───────────────────────────────────────────────────
        migrations.CreateModel(
            name="GameQuestion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("game_type",        models.CharField(max_length=30, choices=[
                    ("sentence_builder", "Sentence Builder"),
                    ("true_or_false",    "True or False"),
                ])),
                ("arabic_sentence",  models.CharField(max_length=300)),
                ("english_sentence", models.CharField(blank=True, max_length=300)),
                ("emoji",            models.CharField(blank=True, max_length=10)),
                ("word_tokens",      models.JSONField(blank=True, default=list, help_text="Word tiles in display order")),
                ("is_true",          models.BooleanField(blank=True, null=True, help_text="Correct answer for True-or-False")),
                ("is_active",        models.BooleanField(default=True)),
                ("created_at",       models.DateTimeField(auto_now_add=True)),
                ("level", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="game_questions",
                    to="curriculum.level",
                )),
                ("course", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="game_questions",
                    to="curriculum.course",
                )),
                ("created_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="game_questions_created",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "game question",
                "verbose_name_plural": "game questions",
                "ordering": ["level__order", "id"],
            },
        ),

    ]

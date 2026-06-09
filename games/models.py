"""
games/models.py

Two models that move game content out of hardcoded JS and into the DB:

  VocabWord    — every Arabic word used by Word Builder, Match Pairs,
                 Missing Letter, True-or-False, and Word Hunt.
  GameQuestion — sentence-level items for Sentence Builder and
                 True-or-False questions that need a full sentence.
"""

from django.conf import settings
from django.db import models


# ─────────────────────────────────────────────────────────────
#  VocabWord
# ─────────────────────────────────────────────────────────────
class VocabWord(models.Model):
    """
    A single Arabic vocabulary item used across multiple games.

    `letters` stores the individual letter tiles as a JSON array, e.g.
        ["ك", "ت", "ا", "ب"]
    `context_forms` stores the contextual (joined) shapes for Word Builder,
        e.g. ["كـ", "ـتـ", "ـا", "ب"]

    Both fields are optional — games that don't need them will ignore them.
    """

    # ── Content ──
    arabic       = models.CharField(max_length=100, help_text="Full Arabic word with tashkeel, e.g. كِتَاب")
    english      = models.CharField(max_length=120, help_text="English translation, e.g. Book")
    emoji        = models.CharField(max_length=10,  blank=True, help_text="Optional emoji, e.g. 📚")
    phonetic     = models.CharField(max_length=120, blank=True, help_text="Romanised pronunciation, e.g. kitāb")

    # Letter-tile data (only needed for Word Builder)
    letters       = models.JSONField(default=list, blank=True,
                                     help_text='Individual letter tiles, e.g. ["ك","ت","ا","ب"]')
    context_forms = models.JSONField(default=list, blank=True,
                                     help_text='Contextual shapes for Word Builder, e.g. ["كـ","ـتـ","ـا","ب"]')

    # Missing-letter data (only needed for Missing Letter game)
    missing_index = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="0-based index of the missing letter in the `letters` array"
    )
    wrong_choices = models.JSONField(default=list, blank=True,
                                     help_text='2 wrong letter choices, e.g. ["ن","م"]')

    # ── Curriculum links ──
    level = models.ForeignKey(
        "curriculum.Level",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="vocab_words",
        help_text="CEFR level this word belongs to (leave blank = all levels)",
    )
    course = models.ForeignKey(
        "curriculum.Course",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="vocab_words",
        help_text="Optional: pin this word to a specific course",
    )

    # ── Flags ──
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide from games")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="vocab_words_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["level__order", "english"]
        verbose_name = "vocabulary word"
        verbose_name_plural = "vocabulary words"

    def __str__(self):
        level_tag = f"[{self.level.code}] " if self.level else ""
        return f"{level_tag}{self.arabic} — {self.english}"


# ─────────────────────────────────────────────────────────────
#  GameQuestion
# ─────────────────────────────────────────────────────────────
class GameQuestion(models.Model):
    """
    A sentence-level question used by Sentence Builder and True-or-False.

    For Sentence Builder:
      `arabic_sentence` holds the full sentence.
      `word_tokens`     holds the shuffled word tiles as a JSON array.
      `english_sentence` is shown as a hint.

    For True-or-False:
      `arabic_sentence` is the statement shown to the student.
      `is_true`         is the correct answer.
      `emoji`           is the picture clue.
    """

    class GameType(models.TextChoices):
        SENTENCE_BUILDER = "sentence_builder", "Sentence Builder"
        TRUE_OR_FALSE    = "true_or_false",    "True or False"

    game_type        = models.CharField(max_length=30, choices=GameType.choices)
    arabic_sentence  = models.CharField(max_length=300)
    english_sentence = models.CharField(max_length=300, blank=True)
    emoji            = models.CharField(max_length=10, blank=True)

    # Sentence Builder only
    word_tokens = models.JSONField(
        default=list, blank=True,
        help_text='Word tiles in display order, e.g. ["أنا","أذهب","إلى","المدرسة"]'
    )

    # True-or-False only
    is_true = models.BooleanField(
        null=True, blank=True,
        help_text="Correct answer for True-or-False questions"
    )

    # Curriculum links
    level = models.ForeignKey(
        "curriculum.Level",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="game_questions",
    )
    course = models.ForeignKey(
        "curriculum.Course",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="game_questions",
    )

    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="game_questions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["level__order", "id"]
        verbose_name = "game question"
        verbose_name_plural = "game questions"

    def __str__(self):
        return f"[{self.get_game_type_display()}] {self.arabic_sentence[:60]}"


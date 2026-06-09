"""
flashcards/models.py

Three tables:

  FlashcardDeck     — a set of cards attached to a lesson
  Flashcard         — one card (front, back, optional audio + notes)
  FlashcardReview   — one student's per-card progress

The schema is deliberately simple — no spaced-repetition scheduling
math yet (no SM-2/Anki intervals). We track times seen, times correct,
last seen, and a "mastered" flag flipped after a streak. Spaced
repetition can be layered on top later by adding a `next_due_at` field
and a scheduling helper.
"""

from django.db import models


# =========================================================
# FlashcardDeck — a set of cards belonging to a lesson
# =========================================================
class FlashcardDeck(models.Model):
    """
    A study deck. Each deck belongs to exactly one lesson — typically a
    vocabulary deck for that lesson's word list, or a verb-conjugation
    drill for a grammar lesson.
    """

    lesson = models.ForeignKey(
        "curriculum.Lesson",
        on_delete=models.CASCADE,
        related_name="flashcard_decks",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(
        default=True,
        help_text="Unpublished decks are hidden from students.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["lesson", "title"]
        verbose_name = "flashcard deck"
        verbose_name_plural = "flashcard decks"

    def __str__(self):
        return f"{self.lesson.title} · {self.title}"


# =========================================================
# Flashcard — one card
# =========================================================
class Flashcard(models.Model):
    """
    A single card.

    Front and back are short strings. `front_lang` / `back_lang` (ISO
    639-1 codes) drive the lang= attribute in templates so Arabic gets
    the proper RTL font + shaping. Audio is optional — a single MP3
    pronouncing the front-side word is the most common case.
    """

    deck = models.ForeignKey(
        FlashcardDeck,
        on_delete=models.CASCADE,
        related_name="cards",
    )
    order = models.PositiveSmallIntegerField()
    front = models.CharField(
        max_length=400,
        help_text="Front side, typically the Arabic word or phrase.",
    )
    back = models.CharField(
        max_length=400,
        help_text="Back side, typically the English translation.",
    )
    front_lang = models.CharField(
        max_length=8,
        default="ar",
        help_text="ISO 639-1 (e.g. 'ar', 'en'). Drives template lang= "
                  "for correct font + shaping.",
    )
    back_lang = models.CharField(max_length=8, default="en")
    audio = models.FileField(
        upload_to="flashcard_audio/",
        null=True,
        blank=True,
        help_text="Optional audio file pronouncing the front-side word.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional usage hints, example sentences, or grammar tips.",
    )

    class Meta:
        ordering = ["deck", "order"]
        constraints = [
            # Two cards in the same deck can't share an order.
            models.UniqueConstraint(
                fields=["deck", "order"],
                name="flashcard_unique_order_per_deck",
            ),
        ]
        verbose_name = "flashcard"
        verbose_name_plural = "flashcards"

    def __str__(self):
        return f"{self.front} / {self.back}"


# =========================================================
# FlashcardReview — one student's per-card progress
# =========================================================
class FlashcardReview(models.Model):
    """
    Tracks how a student is doing on a specific card.

    Updated each time the student marks the card "got it" or "didn't
    get it" during a study session. `is_mastered` flips True after the
    student gets the same card right 3 times in a row — a simple
    heuristic that beats nothing without the complexity of full SM-2
    spaced repetition.
    """

    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="flashcard_reviews",
    )
    flashcard = models.ForeignKey(
        Flashcard,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    times_seen = models.PositiveIntegerField(default=0)
    times_correct = models.PositiveIntegerField(default=0)
    streak = models.PositiveSmallIntegerField(
        default=0,
        help_text="Current correct-in-a-row count. Resets on miss.",
    )
    is_mastered = models.BooleanField(default=False)

    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_correct_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["student", "flashcard"]
        constraints = [
            # One review row per (student, flashcard).
            models.UniqueConstraint(
                fields=["student", "flashcard"],
                name="review_unique_student_card",
            ),
        ]
        verbose_name = "flashcard review"
        verbose_name_plural = "flashcard reviews"

    def __str__(self):
        return f"{self.student} · {self.flashcard.front}"

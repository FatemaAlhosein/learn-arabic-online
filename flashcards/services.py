"""
flashcards/services.py

Review-marking logic. Single source of truth for "the student says
they got it right (or wrong)" — keeps the view tiny.
"""

from django.utils import timezone

from .models import FlashcardReview


# After this many consecutive correct, the card is considered mastered.
STREAK_FOR_MASTERY = 3


def mark_review(student, flashcard, got_it: bool) -> FlashcardReview:
    """
    Record one review of one card by one student.

    Idempotent in the sense that the FlashcardReview row is upserted —
    re-marking the same card just bumps the counters again.

    Returns the updated FlashcardReview.
    """
    review, _ = FlashcardReview.objects.get_or_create(
        student=student,
        flashcard=flashcard,
    )

    review.times_seen += 1
    review.last_seen_at = timezone.now()

    if got_it:
        review.times_correct += 1
        review.streak += 1
        review.last_correct_at = timezone.now()
        if review.streak >= STREAK_FOR_MASTERY:
            review.is_mastered = True
    else:
        review.streak = 0
        review.is_mastered = False  # missed → no longer mastered

    review.save()
    return review

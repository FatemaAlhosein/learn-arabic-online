"""
curriculum/signals.py

When a LessonProgress is saved with status=COMPLETED, call
maybe_complete_enrollment() to check whether the whole course is now
done, and if so auto-issue the certificate.

Signals are registered when Django starts via curriculum/apps.py:ready().
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LessonProgress


@receiver(post_save, sender=LessonProgress)
def on_lesson_progress_save(sender, instance, **kwargs):
    """
    Fires after every LessonProgress save.

    Only proceeds if the lesson was just marked COMPLETED — avoids running
    the DB check on every unrelated update (e.g. last_viewed_at stamps).
    """
    if instance.status != LessonProgress.Status.COMPLETED:
        return

    from .services import maybe_complete_enrollment
    completed = maybe_complete_enrollment(instance.enrollment)

    if completed:
        # Import here to avoid circular imports at module load time.
        # Notify the student and (if applicable) their parents.
        try:
            from notifications.services import notify_course_completed
            notify_course_completed(instance.enrollment)
        except Exception:
            # Notifications failing should never break lesson completion.
            pass

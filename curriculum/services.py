"""
curriculum/services.py

Business logic that doesn't fit naturally on a single model.

Right now this file holds the eligibility rules — the single source of truth
for "can this student enrol in this course?". Views, forms, and templates all
call into here so the rules can never drift.

Design: pure functions taking model instances, returning either a bool or
a small dataclass. No side effects, no DB writes — those happen in views.
"""

from dataclasses import dataclass


# =========================================================
# Eligibility result
# =========================================================
@dataclass(frozen=True)
class Eligibility:
    """
    Verdict from `student_can_enroll`.

    `ok` is the bool a view typically branches on. `reason` is a stable
    machine-readable code (for translations / analytics), and `message` is
    the human-readable string we show in the UI.

    Reason codes:
        ok                 -> all checks passed
        wrong_track        -> course is for a different age group
        no_level           -> student has no current_level yet (placement needed)
        below_prereq       -> student is more than one level below the course
        course_unpublished -> course is hidden from the catalogue
        already_enrolled   -> caller can decide whether to treat this as ok or not
    """

    ok: bool
    reason: str
    message: str


# =========================================================
# The three rules
# =========================================================
def _track_matches(student, course) -> bool:
    """
    Track rule:
        course.track == 'all'            -> always ok
        course.track == student.age_track -> ok
        otherwise                         -> blocked
    """
    if course.track == course.Track.ALL:
        return True
    return course.track == student.age_track


def _level_ok(student, course) -> Eligibility | None:
    """
    Level rule:
        course.level is None  -> open course, ok regardless of student level
        student.current_level is None -> blocked (no placement yet)
        student.current_level.order >= course.level.order - 1 -> ok
            (next-level rule: a B1 student can take B1 or B2, but not C1)
        otherwise -> blocked

    Returns None if the rule passes (so the caller continues checking).
    Returns an Eligibility(ok=False, ...) if it fails.
    """
    if course.level_id is None:
        return None  # open course, no level check

    if student.current_level_id is None:
        return Eligibility(
            ok=False,
            reason="no_level",
            message=("Take the placement test first so we can match you "
                     "to the right courses."),
        )

    if student.current_level.order >= course.level.order - 1:
        return None

    return Eligibility(
        ok=False,
        reason="below_prereq",
        message=(f"You're at {student.current_level.code}; this course "
                 f"requires {course.level.code} or one level below."),
    )


# =========================================================
# Public API
# =========================================================
def student_can_enroll(student, course) -> Eligibility:
    """
    Single source of truth for enrolment eligibility.

    Rules, in this order:
      1. Course must be published.
      2. Track must match (or be 'all').
      3. Level prereq must hold (or course must be open).

    The "already enrolled" check is NOT performed here. That's a database
    question (does an Enrollment row already exist?) and the caller is
    in a better position to decide whether re-enrolment is allowed
    (e.g. if the previous enrolment was cancelled).
    """
    # 1. Published?
    if not course.is_published:
        return Eligibility(
            ok=False,
            reason="course_unpublished",
            message="This course isn't available right now.",
        )

    # 2. Age track.
    if not _track_matches(student, course):
        return Eligibility(
            ok=False,
            reason="wrong_track",
            message=("This course is intended for a different age group "
                     f"({course.get_track_display()})."),
        )

    # 3. Level prereq.
    level_problem = _level_ok(student, course)
    if level_problem is not None:
        return level_problem

    # All checks passed.
    return Eligibility(
        ok=True,
        reason="ok",
        message="You can enrol in this course.",
    )


# =========================================================
# Certificate / course-completion helper
# =========================================================
import secrets
import string

from django.utils import timezone


def maybe_complete_enrollment(enrollment) -> bool:
    """
    Check whether `enrollment` is now fully complete (all lessons done).
    If so, stamp it as 'completed', generate a certificate_code, and
    set completed_at.  Returns True if the enrollment was just completed.

    Safe to call multiple times — if already completed, this is a no-op.
    """
    from .models import Enrollment, Lesson, LessonProgress  # local to avoid circular

    if enrollment.status == Enrollment.Status.COMPLETED:
        return False  # already done, nothing to do

    total_lessons = Lesson.objects.filter(course=enrollment.course).count()
    if total_lessons == 0:
        return False  # empty course, don't auto-complete

    done_lessons = LessonProgress.objects.filter(
        enrollment=enrollment,
        status=LessonProgress.Status.COMPLETED,
    ).count()

    if done_lessons < total_lessons:
        return False  # not there yet

    # All lessons completed — issue certificate!
    code = _generate_certificate_code()
    enrollment.status = Enrollment.Status.COMPLETED
    enrollment.completed_at = timezone.now()
    enrollment.certificate_code = code
    enrollment.save(update_fields=["status", "completed_at", "certificate_code"])
    return True


def _generate_certificate_code(length: int = 32) -> str:
    """
    Return a cryptographically random, URL-safe certificate code.
    Uses digits + uppercase letters only so the code is visually clean
    when printed on a certificate.
    """
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

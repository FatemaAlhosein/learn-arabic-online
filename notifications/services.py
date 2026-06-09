"""
notifications/services.py

All the places that need to fire a notification call one of the helpers here.
This keeps trigger logic out of views, signals, and models.

Usage:
    from notifications.services import notify_assignment_submitted
    notify_assignment_submitted(submission)
"""

from django.urls import reverse

from .models import Notification


# ── Low-level helper ─────────────────────────────────────────────────────────

def create_notification(recipient, kind, message, link=""):
    """Create a single Notification row. Returns the saved instance."""
    return Notification.objects.create(
        recipient=recipient,
        kind=kind,
        message=message,
        link=link,
    )


# ── Course / enrollment triggers ─────────────────────────────────────────────

def notify_enrollment(enrollment):
    """
    Student enrolled in a course.
    Sends to: student, course teacher.
    """
    student_user = enrollment.student.user
    course = enrollment.course

    # To student
    create_notification(
        recipient=student_user,
        kind=Notification.Kind.ENROLLMENT,
        message=f'You have been enrolled in "{course.title}".',
        link=reverse("curriculum:course_detail", args=[course.slug]),
    )

    # To teacher
    student_name = (
        student_user.get_full_name() or student_user.email
    )
    create_notification(
        recipient=course.teacher,
        kind=Notification.Kind.NEW_ENROLLMENT,
        message=f'{student_name} enrolled in "{course.title}".',
        link=reverse("student_progress", args=[student_user.id]),
    )


def notify_course_completed(enrollment):
    """
    Student completed all lessons in a course → certificate issued.
    Sends to: student, any linked parents.
    """
    student_user = enrollment.student.user
    course = enrollment.course
    cert_link = enrollment.get_certificate_path()

    student_name = student_user.get_full_name() or student_user.email

    # To student
    create_notification(
        recipient=student_user,
        kind=Notification.Kind.COURSE_DONE,
        message=f'🎉 You completed "{course.title}"! Your certificate is ready.',
        link=cert_link,
    )

    # To linked parent (StudentProfile has a single `parent` FK)
    try:
        parent_profile = enrollment.student.parent
        if parent_profile:
            create_notification(
                recipient=parent_profile.user,
                kind=Notification.Kind.CHILD_COURSE_DONE,
                message=(
                    f'{student_name} completed "{course.title}"! '
                    f'View their certificate.'
                ),
                link=cert_link,
            )
    except Exception:
        pass  # no parent linked — not an error


# ── Assignment triggers ───────────────────────────────────────────────────────

def notify_assignment_submitted(submission):
    """
    Student submitted an assignment.
    Sends to: course teacher.
    """
    student_user = submission.student
    assignment = submission.assignment
    course = assignment.course

    student_name = student_user.get_full_name() or student_user.email

    try:
        link = reverse("assignments:submission_detail", args=[submission.id])
    except Exception:
        link = ""

    create_notification(
        recipient=course.teacher,
        kind=Notification.Kind.ASSIGNMENT_SUBMITTED,
        message=(
            f'{student_name} submitted "{assignment.title}" '
            f'in "{course.title}".'
        ),
        link=link,
    )


def notify_assignment_graded(submission):
    """
    Teacher graded a submission.
    Sends to: student.
    """
    student_user = submission.student
    assignment = submission.assignment

    score_text = ""
    if submission.score is not None:
        score_text = f" — score: {submission.score}/{assignment.max_score}"

    try:
        link = reverse("assignments:my_submission", args=[submission.id])
    except Exception:
        link = ""

    create_notification(
        recipient=student_user,
        kind=Notification.Kind.ASSIGNMENT_GRADED,
        message=f'Your assignment "{assignment.title}" has been graded{score_text}.',
        link=link,
    )


# ── Quiz trigger ─────────────────────────────────────────────────────────────

def notify_quiz_result(submission):
    """
    Student completed a quiz.
    Sends to: student.
    """
    student_user = submission.student
    quiz = submission.quiz

    if submission.passed is True:
        msg = f'You passed the quiz "{quiz.title}"! Well done.'
        kind = Notification.Kind.QUIZ_RESULT
    elif submission.passed is False:
        msg = f'You did not pass "{quiz.title}" this time. Try again!'
        kind = Notification.Kind.QUIZ_RESULT
    else:
        return  # no result yet

    create_notification(
        recipient=student_user,
        kind=kind,
        message=msg,
        link="",
    )

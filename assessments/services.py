"""
assessments/services.py

Quiz business logic that doesn't fit on a model.

  grade_submission(submission)
      Score every Answer, sum the points, decide pass/fail, update the
      Submission. Calls apply_pass_effects() once the submission is fully
      graded so the rest of the app reacts.

  apply_pass_effects(submission)
      Side-effect dispatcher.
        lesson_quiz pass  -> mark LessonProgress completed
        course_final pass -> mark Enrollment completed + mint cert
        placement         -> ALWAYS write StudentProfile.current_level
                             (no pass/fail; the score band picks the level)
"""

import secrets

from django.utils import timezone

from curriculum.models import Enrollment, Level, LessonProgress

from .models import Answer, Question, Quiz, Submission


# =========================================================
# Placement score bands — score% -> CEFR level code
# =========================================================
# Highest threshold first; each band is "score >= min_score".
# A1 is the floor — anyone who took the test gets at least A1.
PLACEMENT_BANDS = [
    (95, "C2"),
    (85, "C1"),
    (70, "B2"),
    (50, "B1"),
    (30, "A2"),
    (0,  "A1"),
]


def _level_code_for_score(score: int) -> str:
    """Map a placement score (0–100) to a CEFR code via PLACEMENT_BANDS."""
    for threshold, code in PLACEMENT_BANDS:
        if score >= threshold:
            return code
    return "A1"  # safety net; PLACEMENT_BANDS already includes 0 -> A1


# =========================================================
# Per-question grading
# =========================================================
def grade_answer(answer: Answer) -> bool | None:
    """
    Score a single Answer row.

    Returns:
        True   -> question was auto-graded as correct
        False  -> question was auto-graded as incorrect
        None   -> question is short_answer; needs a teacher

    Side effect: writes `is_correct` and `points_awarded` on the Answer.
    """
    question = answer.question

    # Short-answer: teacher grades; leave alone, signal "manual needed".
    if question.kind == Question.Kind.SHORT_ANSWER:
        return None

    # Choice-based questions: compare the SET of correct choice IDs to
    # the SET of selected choice IDs. A correct submission needs both
    # equal — picking too few or too many is wrong.
    correct_ids = set(
        question.choices.filter(is_correct=True).values_list("id", flat=True)
    )
    selected_ids = set(
        answer.selected_choices.values_list("id", flat=True)
    )

    is_correct = (selected_ids == correct_ids)

    answer.is_correct = is_correct
    answer.points_awarded = question.points if is_correct else 0
    answer.save(update_fields=["is_correct", "points_awarded"])
    return is_correct


# =========================================================
# Whole-submission grading
# =========================================================
def grade_submission(submission: Submission) -> Submission:
    """
    Grade every answer on this submission, then update score / passed /
    status on the Submission itself.

    Two outcomes:
      - All answers auto-gradable -> status='graded', score set, passed set
      - Any short_answer present  -> status stays 'submitted', score and
                                     passed stay None until the teacher
                                     grades the short-answer rows in admin

    Idempotent: re-running on a graded submission is a no-op (no
    over-counting), but will refresh derived fields if the underlying
    answers changed (e.g., teacher edited a short-answer mark).
    """
    quiz = submission.quiz

    # Make sure every question has an Answer row — students may have
    # navigated past a question without selecting anything. Create empty
    # Answer rows so the grader doesn't silently skip them.
    answered_q_ids = set(
        submission.answers.values_list("question_id", flat=True)
    )
    for question in quiz.questions.all():
        if question.id not in answered_q_ids:
            Answer.objects.create(
                submission=submission,
                question=question,
            )

    # Grade each answer.
    answers = list(
        submission.answers
        .select_related("question")
        .prefetch_related("selected_choices", "question__choices")
    )

    needs_manual = False
    earned = 0
    for a in answers:
        result = grade_answer(a)
        if result is None:
            needs_manual = True
        else:
            earned += a.points_awarded or 0

    total_points = sum(q.points for q in quiz.questions.all())

    # Until manual grading is in, short-answer questions count as 0;
    # we still compute the auto-only percentage so the student gets
    # *some* feedback. Once the teacher grades the short-answer rows
    # and re-runs grade_submission, the score updates.
    if total_points > 0:
        # Add manual points already awarded (teacher edited admin earlier).
        manual_earned = sum(
            (a.points_awarded or 0)
            for a in answers
            if a.question.kind == Question.Kind.SHORT_ANSWER
        )
        earned += manual_earned
        score_pct = int(round(100 * earned / total_points))
    else:
        score_pct = 0

    submission.score = score_pct
    submission.passed = (score_pct >= quiz.pass_threshold)

    # Status: graded only if no manual work pending.
    if needs_manual and not _all_short_answers_graded(submission):
        submission.status = Submission.Status.SUBMITTED
    else:
        submission.status = Submission.Status.GRADED
        submission.graded_at = timezone.now()

    submission.save(update_fields=[
        "score", "passed", "status", "graded_at"
    ])

    # Once a submission is fully graded, propagate downstream effects.
    if submission.status == Submission.Status.GRADED:
        apply_pass_effects(submission)

    return submission


def apply_pass_effects(submission: Submission) -> None:
    """
    React to a graded submission. Idempotent across re-runs.

      lesson_quiz pass   -> LessonProgress.status = COMPLETED
      course_final pass  -> Enrollment.status = COMPLETED + certificate
      placement          -> always: write StudentProfile.current_level

    Note the asymmetry: lesson/course-final require submission.passed
    (a failing attempt is a silent no-op). Placement runs unconditionally
    because the *score band*, not pass/fail, is what selects the level.
    """
    quiz = submission.quiz
    student = submission.student

    # Placement runs first and unconditionally.
    if quiz.kind == Quiz.Kind.PLACEMENT:
        _apply_placement_effect(submission)
        return

    # Other kinds only propagate on a passing submission.
    if not submission.passed:
        return

    if quiz.kind == Quiz.Kind.LESSON_QUIZ and quiz.lesson_id:
        # Find the student's enrolment in this lesson's course. If they
        # aren't enrolled, skip — this can happen when a free-preview
        # lesson has a quiz and the student took it without enroling.
        enrollment = Enrollment.objects.filter(
            student=student,
            course=quiz.lesson.course,
        ).first()
        if enrollment is None:
            return

        progress, _ = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=quiz.lesson,
            defaults={
                "status": LessonProgress.Status.COMPLETED,
                "completed_at": timezone.now(),
            },
        )
        if progress.status != LessonProgress.Status.COMPLETED:
            progress.status = LessonProgress.Status.COMPLETED
            progress.completed_at = timezone.now()
            progress.save(update_fields=["status", "completed_at"])

    elif quiz.kind == Quiz.Kind.COURSE_FINAL and quiz.course_id:
        enrollment = Enrollment.objects.filter(
            student=student,
            course=quiz.course,
        ).first()
        if enrollment is None:
            return

        if enrollment.status != Enrollment.Status.COMPLETED:
            enrollment.status = Enrollment.Status.COMPLETED
            enrollment.completed_at = timezone.now()
            if not enrollment.certificate_code:
                # 16 bytes -> 32 hex chars. Plenty of entropy; not
                # guessable, not enumerable.
                enrollment.certificate_code = secrets.token_hex(16)
            enrollment.save(update_fields=[
                "status", "completed_at", "certificate_code"
            ])


def _apply_placement_effect(submission: Submission) -> None:
    """
    Write the student's current_level based on the placement score band.

    A re-take always overwrites — the student knows whether they want
    to take the test again, and the new result reflects their current
    knowledge, not the historical first impression. The previous
    Submission row remains untouched in the audit trail.
    """
    score = submission.score or 0
    target_code = _level_code_for_score(score)
    target_level = Level.objects.filter(code=target_code).first()
    if target_level is None:
        # CEFR levels weren't seeded — silent no-op rather than a 500.
        return

    student = submission.student
    if student.current_level_id == target_level.id:
        return  # already at this level; idempotent

    student.current_level = target_level
    student.save(update_fields=["current_level"])


def _all_short_answers_graded(submission: Submission) -> bool:
    """
    True iff every short_answer Answer on this submission has
    points_awarded set (teacher has graded them all).
    """
    pending = (
        submission.answers
        .filter(question__kind=Question.Kind.SHORT_ANSWER)
        .filter(points_awarded__isnull=True)
        .exists()
    )
    return not pending

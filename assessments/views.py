"""
assessments/views.py

Quiz player flow (Option B — one question per page).

  GET  /quizzes/<id>/                                       quiz_intro
  POST /quizzes/<id>/start/                                 start_quiz
  GET  /submissions/<id>/q/<order>/                         take_question (render)
  POST /submissions/<id>/q/<order>/                         take_question (save + nav)
  POST /submissions/<id>/submit/                            submit_quiz
  GET  /submissions/<id>/                                   submission_result

Access rules:
  - Anonymous users get bounced to /accounts/login/.
  - Only the student who owns a submission can view or modify it.
  - A submission's status must be in_progress to save answers.
  - Once submitted, the result page is read-only.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Answer, Question, Quiz, Submission
from .services import grade_submission


# =========================================================
# Helpers
# =========================================================
def _get_student_or_403(request):
    """Return the StudentProfile or raise 404 for non-students."""
    if not request.user.is_student:
        raise Http404("Only students can take quizzes.")
    student = getattr(request.user, "student_profile", None)
    if student is None:
        raise Http404("Student profile missing.")
    return student


def _get_owned_submission(request, submission_id):
    """Fetch a submission, ensuring the requesting user owns it."""
    student = _get_student_or_403(request)
    return get_object_or_404(
        Submission.objects.select_related("quiz", "student"),
        pk=submission_id,
        student=student,
    )


# =========================================================
# Quiz intro — /quizzes/<id>/
# =========================================================
@login_required
def quiz_intro(request, quiz_id):
    """
    Landing page before starting a quiz.

    Shows: title, description, question count, pass threshold, time limit,
    plus the student's past attempts and a Start (or Resume) button.
    """
    student = _get_student_or_403(request)
    quiz = get_object_or_404(
        Quiz.objects.prefetch_related("questions"),
        pk=quiz_id,
        is_published=True,
    )

    in_progress = (
        Submission.objects
        .filter(quiz=quiz, student=student,
                status=Submission.Status.IN_PROGRESS)
        .first()
    )
    past_attempts = (
        Submission.objects
        .filter(quiz=quiz, student=student)
        .exclude(status=Submission.Status.IN_PROGRESS)
        .order_by("-started_at")[:5]
    )

    return render(request, "assessments/quiz_intro.html", {
        "quiz": quiz,
        "question_count": quiz.questions.count(),
        "in_progress": in_progress,
        "past_attempts": past_attempts,
    })


# =========================================================
# Start (or resume) a quiz attempt — POST /quizzes/<id>/start/
# =========================================================
@login_required
@require_POST
def start_quiz(request, quiz_id):
    """
    Create a new in_progress Submission, OR resume the student's existing
    one. Redirect to the first question either way.
    """
    student = _get_student_or_403(request)
    quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)

    # If the quiz has no questions, we can't start.
    first_q = quiz.questions.order_by("order").first()
    if first_q is None:
        messages.warning(request, "This quiz has no questions yet.")
        return HttpResponseRedirect(
            reverse("assessments:quiz_intro", args=[quiz.id])
        )

    submission, _ = Submission.objects.get_or_create(
        quiz=quiz,
        student=student,
        status=Submission.Status.IN_PROGRESS,
        defaults={},
    )

    return HttpResponseRedirect(reverse(
        "assessments:take_question",
        args=[submission.id, first_q.order],
    ))


# =========================================================
# Take one question — /submissions/<id>/q/<order>/
# =========================================================
@login_required
def take_question(request, submission_id, order):
    """
    GET  -> render the question with the student's previous answer pre-filled.
    POST -> persist the answer (upsert), then navigate based on which
            button was pressed: 'prev', 'next', or 'finish'.

    The 'finish' button only appears on the last question; a POST with
    'finish' is what closes out an attempt.
    """
    submission = _get_owned_submission(request, submission_id)
    quiz = submission.quiz

    # No editing once submitted.
    if submission.status != Submission.Status.IN_PROGRESS:
        return HttpResponseRedirect(
            reverse("assessments:submission_result", args=[submission.id])
        )

    questions = list(quiz.questions.order_by("order")
                     .prefetch_related("choices"))
    if not questions:
        raise Http404("Quiz has no questions.")

    # Locate this question.
    try:
        question = next(q for q in questions if q.order == int(order))
    except (ValueError, StopIteration):
        raise Http404("Question not found.")

    idx = questions.index(question)
    prev_q = questions[idx - 1] if idx > 0 else None
    next_q = questions[idx + 1] if idx + 1 < len(questions) else None
    is_last = next_q is None

    # The existing Answer (if the student has touched this question before).
    answer = (
        Answer.objects
        .prefetch_related("selected_choices")
        .filter(submission=submission, question=question)
        .first()
    )

    if request.method == "POST":
        answer = _save_answer(request, submission, question, answer)

        action = request.POST.get("action", "next")
        if action == "prev" and prev_q:
            return HttpResponseRedirect(reverse(
                "assessments:take_question",
                args=[submission.id, prev_q.order],
            ))
        if action == "finish" and is_last:
            # Finalise inline — we can't redirect from a POST to another
            # POST endpoint (the browser would downgrade it to GET).
            return _finalize_submission(request, submission)
        # Default: 'next', or 'finish' on a non-last (defensive fallback).
        if next_q:
            return HttpResponseRedirect(reverse(
                "assessments:take_question",
                args=[submission.id, next_q.order],
            ))
        # No next AND not finish? Bounce to intro as a fallback.
        return HttpResponseRedirect(
            reverse("assessments:quiz_intro", args=[quiz.id])
        )

    # GET — pre-fill from saved answer.
    selected_choice_ids = (
        set(answer.selected_choices.values_list("id", flat=True))
        if answer else set()
    )

    return render(request, "assessments/take_question.html", {
        "submission": submission,
        "quiz": quiz,
        "question": question,
        "questions": questions,
        "current_index": idx,
        "total": len(questions),
        "prev_q": prev_q,
        "next_q": next_q,
        "is_last": is_last,
        "answer": answer,
        "selected_choice_ids": selected_choice_ids,
    })


def _save_answer(request, submission, question, answer):
    """
    Upsert an Answer row from the POST data.

    Logic per question kind:
        mcq           -> read 'choice' (single radio value)
        multi_select  -> read 'choice' as a list (checkboxes share name)
        true_false    -> read 'choice' (single radio)
        short_answer  -> read 'text_answer'

    Saving an empty answer is allowed (the student is just navigating);
    we still write the row so we can tell the question was visited.
    """
    if answer is None:
        answer = Answer(submission=submission, question=question)
        answer.save()  # need pk before we can attach M2M choices

    if question.kind == Question.Kind.SHORT_ANSWER:
        answer.text_answer = request.POST.get("text_answer", "").strip()
        answer.selected_choices.clear()
    else:
        # Choice-based.
        ids = request.POST.getlist("choice")
        # mcq + true_false should only have one; we trust the radio UI.
        valid_ids = list(
            question.choices.filter(id__in=ids).values_list("id", flat=True)
        )
        answer.text_answer = ""
        answer.selected_choices.set(valid_ids)

    # is_correct / points_awarded stay None until the grader runs (Phase 6C).
    answer.save()
    return answer


# =========================================================
# Submit — POST /submissions/<id>/submit/
# =========================================================
def _finalize_submission(request, submission):
    """
    Shared finaliser — called both by submit_quiz (direct POST) and by
    take_question's 'finish' action. Idempotent on already-submitted rows.

    Side effects:
      - flips status -> SUBMITTED, stamps submitted_at
      - runs the grader (which may flip status -> GRADED + apply effects)
      - adds a flash message tailored to the quiz kind

    Returns a redirect to the submission result page.
    """
    if submission.status == Submission.Status.IN_PROGRESS:
        submission.status = Submission.Status.SUBMITTED
        submission.submitted_at = timezone.now()
        submission.save(update_fields=["status", "submitted_at"])

        grade_submission(submission)

        # Fire quiz-result notification (non-placement quizzes only)
        if (submission.status == Submission.Status.GRADED
                and submission.quiz.kind != Quiz.Kind.PLACEMENT):
            try:
                from notifications.services import notify_quiz_result
                notify_quiz_result(submission)
            except Exception:
                pass

        if submission.status == Submission.Status.GRADED:
            if submission.quiz.kind == Quiz.Kind.PLACEMENT:
                # Placement: report the assigned level instead of pass/fail.
                student = submission.student
                student.refresh_from_db(fields=["current_level"])
                if student.current_level_id:
                    messages.success(
                        request,
                        f"Placement complete — you're at "
                        f"{student.current_level.code} "
                        f"({student.current_level.name}).",
                    )
                else:
                    messages.info(request, "Placement recorded.")
            elif submission.passed:
                messages.success(
                    request,
                    f"You scored {submission.score}% — passed!",
                )
            else:
                messages.warning(
                    request,
                    f"You scored {submission.score}%. "
                    f"Pass threshold is {submission.quiz.pass_threshold}%.",
                )
        else:
            messages.info(
                request,
                "Your answers are recorded. Some questions need teacher "
                "grading; you'll see your final score once they're reviewed.",
            )

    return HttpResponseRedirect(
        reverse("assessments:submission_result", args=[submission.id])
    )


@login_required
@require_POST
def submit_quiz(request, submission_id):
    """Finalise + grade. Direct POST entry point (kept for completeness)."""
    submission = _get_owned_submission(request, submission_id)
    return _finalize_submission(request, submission)


# =========================================================
# Result — /submissions/<id>/
# =========================================================
@login_required
def submission_result(request, submission_id):
    """
    Read-only view of one submission.

    For placement quizzes, also computes a small set of "recommended
    courses" sized to the student's newly-assigned level + age track.
    Other quiz kinds get an empty list, so the template just hides the
    section.
    """
    submission = _get_owned_submission(request, submission_id)
    answers = (
        submission.answers
        .select_related("question")
        .prefetch_related("selected_choices", "question__choices")
        .order_by("question__order")
    )

    recommended_courses = []
    if (submission.quiz.kind == Quiz.Kind.PLACEMENT
            and submission.status == Submission.Status.GRADED):
        recommended_courses = _recommend_for_placement(submission)

    return render(request, "assessments/submission_result.html", {
        "submission": submission,
        "answers": answers,
        "recommended_courses": recommended_courses,
    })


def _recommend_for_placement(submission):
    """
    Pick up to 6 published courses to suggest after a placement test.

    Logic:
      - At student's level OR one level up OR open (no level)
      - Track must match (or be 'all')
      - Exclude courses the student is already enrolled in
      - Order: same-level first, then next level up, then open
    """
    from django.db.models import Case, IntegerField, Q, Value, When
    from curriculum.models import Course

    student = submission.student
    if student.current_level is None:
        return []

    own_order = student.current_level.order

    enrolled_ids = list(
        student.enrollments.values_list("course_id", flat=True)
    )

    return list(
        Course.objects
        .filter(is_published=True)
        .filter(
            Q(level__order=own_order)
            | Q(level__order=own_order + 1)
            | Q(level__isnull=True)
        )
        .filter(
            Q(track="all") | Q(track=student.age_track)
        )
        .exclude(id__in=enrolled_ids)
        .annotate(
            sort_priority=Case(
                When(level__order=own_order, then=Value(0)),
                When(level__order=own_order + 1, then=Value(1)),
                default=Value(2),  # open courses
                output_field=IntegerField(),
            )
        )
        .select_related("level", "category")
        .order_by("sort_priority", "title")[:6]
    )


# =========================================================
# Teacher — quiz management
# =========================================================
def _require_teacher_quiz(request, quiz):
    """Return error response if request.user is not the quiz's teacher, else None."""
    from accounts.models import User
    from django.http import HttpResponseForbidden
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")
    # Determine ownership through lesson or course FK.
    if quiz.lesson_id and quiz.lesson.course.teacher != request.user:
        return HttpResponseForbidden("You can only manage your own quizzes.")
    if quiz.course_id and quiz.course.teacher != request.user:
        return HttpResponseForbidden("You can only manage your own quizzes.")
    return None


@login_required
def quiz_create(request):
    """Create a new quiz (lesson_quiz or course_final)."""
    from accounts.models import User
    from django.http import HttpResponseForbidden
    from .forms import QuizForm

    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    # Allow pre-filling lesson/course from query string.
    initial = {}
    lesson_id = request.GET.get("lesson")
    course_id = request.GET.get("course")
    if lesson_id:
        from curriculum.models import Lesson
        try:
            initial["lesson"] = Lesson.objects.get(
                pk=lesson_id, course__teacher=request.user
            )
            initial["kind"] = Quiz.Kind.LESSON_QUIZ
        except Lesson.DoesNotExist:
            pass
    elif course_id:
        from curriculum.models import Course
        try:
            initial["course"] = Course.objects.get(
                pk=course_id, teacher=request.user
            )
            initial["kind"] = Quiz.Kind.COURSE_FINAL
        except Course.DoesNotExist:
            pass

    if request.method == "POST":
        form = QuizForm(request.POST, teacher=request.user)
        if form.is_valid():
            quiz = form.save()
            messages.success(request, f'Quiz "{quiz.title}" created.')
            return HttpResponseRedirect(
                reverse("assessments:quiz_manage", args=[quiz.id])
            )
    else:
        form = QuizForm(initial=initial, teacher=request.user)

    return render(request, "assessments/teach/quiz_form.html", {
        "form": form,
        "mode": "create",
        "page_title": "New quiz",
    })


@login_required
def quiz_edit(request, quiz_id):
    """Edit an existing quiz's settings."""
    from .forms import QuizForm
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    err = _require_teacher_quiz(request, quiz)
    if err:
        return err

    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Quiz settings saved.")
            return HttpResponseRedirect(
                reverse("assessments:quiz_manage", args=[quiz.id])
            )
    else:
        form = QuizForm(instance=quiz, teacher=request.user)

    return render(request, "assessments/teach/quiz_form.html", {
        "form": form,
        "quiz": quiz,
        "mode": "edit",
        "page_title": f"Edit quiz — {quiz.title}",
    })


@login_required
def quiz_manage(request, quiz_id):
    """List questions for a quiz; entry point after creating/editing."""
    quiz = get_object_or_404(
        Quiz.objects.prefetch_related("questions__choices"),
        pk=quiz_id,
    )
    err = _require_teacher_quiz(request, quiz)
    if err:
        return err

    return render(request, "assessments/teach/quiz_manage.html", {
        "quiz": quiz,
        "questions": quiz.questions.all(),
    })


@login_required
@require_POST
def quiz_delete(request, quiz_id):
    """Delete a quiz and all its questions."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    err = _require_teacher_quiz(request, quiz)
    if err:
        return err

    # Figure out where to redirect after deletion.
    if quiz.lesson_id:
        back_url = reverse(
            "curriculum:course_manage",
            args=[quiz.lesson.course.slug],
        )
    elif quiz.course_id:
        back_url = reverse(
            "curriculum:course_manage",
            args=[quiz.course.slug],
        )
    else:
        back_url = reverse("dashboard")

    title = quiz.title
    quiz.delete()
    messages.success(request, f'Quiz "{title}" deleted.')
    return HttpResponseRedirect(back_url)


# =========================================================
# Teacher — question management
# =========================================================
@login_required
def question_create(request, quiz_id):
    """Add a question (and its choices) to a quiz."""
    from .forms import ChoiceFormSet, QuestionForm
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    err = _require_teacher_quiz(request, quiz)
    if err:
        return err

    # Suggest next order number.
    next_order = (quiz.questions.count() or 0) + 1

    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.save(commit=False)
            question.quiz = quiz
            question.save()

            # Save choices for non-short-answer questions.
            if question.kind != Question.Kind.SHORT_ANSWER:
                formset = ChoiceFormSet(request.POST, instance=question)
                if formset.is_valid():
                    formset.save()
                    # For true/false, ensure exactly two canonical choices exist.
                    if question.kind == Question.Kind.TRUE_FALSE:
                        _ensure_tf_choices(question)
            messages.success(request, "Question added.")
            return HttpResponseRedirect(
                reverse("assessments:quiz_manage", args=[quiz.id])
            )
        else:
            formset = ChoiceFormSet(request.POST,
                                    instance=Question())
    else:
        form = QuestionForm(initial={"order": next_order})
        formset = ChoiceFormSet(instance=Question())

    return render(request, "assessments/teach/question_form.html", {
        "form": form,
        "formset": formset,
        "quiz": quiz,
        "mode": "create",
        "page_title": "Add question",
    })


@login_required
def question_edit(request, quiz_id, question_id):
    """Edit a question and its choices."""
    from .forms import ChoiceFormSet, QuestionForm
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    err = _require_teacher_quiz(request, quiz)
    if err:
        return err
    question = get_object_or_404(Question, pk=question_id, quiz=quiz)

    if request.method == "POST":
        form = QuestionForm(request.POST, instance=question)
        formset = ChoiceFormSet(request.POST, instance=question)
        if form.is_valid() and (
            question.kind == Question.Kind.SHORT_ANSWER or formset.is_valid()
        ):
            form.save()
            if question.kind != Question.Kind.SHORT_ANSWER:
                formset.save()
                if question.kind == Question.Kind.TRUE_FALSE:
                    _ensure_tf_choices(question)
            messages.success(request, "Question saved.")
            return HttpResponseRedirect(
                reverse("assessments:quiz_manage", args=[quiz.id])
            )
    else:
        form = QuestionForm(instance=question)
        formset = ChoiceFormSet(instance=question)

    return render(request, "assessments/teach/question_form.html", {
        "form": form,
        "formset": formset,
        "quiz": quiz,
        "question": question,
        "mode": "edit",
        "page_title": f"Edit question {question.order}",
    })


@login_required
@require_POST
def question_delete(request, quiz_id, question_id):
    """Delete a single question."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    err = _require_teacher_quiz(request, quiz)
    if err:
        return err
    question = get_object_or_404(Question, pk=question_id, quiz=quiz)
    question.delete()
    messages.success(request, "Question deleted.")
    return HttpResponseRedirect(
        reverse("assessments:quiz_manage", args=[quiz.id])
    )


def _ensure_tf_choices(question):
    """
    Make sure a True/False question has exactly the standard two choices.
    Creates them if they're missing; leaves them if already present.
    """
    existing_texts = set(
        question.choices.values_list("text", flat=True)
    )
    if "True" not in existing_texts:
        Choice.objects.get_or_create(
            question=question,
            text="True",
            defaults={"order": 1, "is_correct": False},
        )
    if "False" not in existing_texts:
        Choice.objects.get_or_create(
            question=question,
            text="False",
            defaults={"order": 2, "is_correct": False},
        )

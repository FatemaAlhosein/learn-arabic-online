"""
assessments/models.py

Five tables for the quiz / placement-test system:

  Quiz       — a set of questions; can belong to a lesson, a course, or
               nothing (placement test)
  Question   — one item in a quiz; has a kind (mcq / multi / tf / short)
  Choice     — one option for a Question (only used by mcq / multi / tf)
  Submission — one student's attempt at one quiz (re-takes get new rows)
  Answer     — one student's response to one question within a Submission

Auto-grading covers mcq, multi_select, true_false. Short-answer is left
manual — teachers grade those in admin (Phase 6C).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


# =========================================================
# Quiz — top-level container
# =========================================================
class Quiz(models.Model):
    """
    A set of questions a student takes in one go.

    `kind` decides what passing the quiz triggers downstream (Phase 6D):
        lesson_quiz   -> mark LessonProgress.completed for `lesson`
        course_final  -> mark Enrollment.completed for `course`
        placement     -> write StudentProfile.current_level (Phase 7)

    Most quizzes are scoped to one lesson OR one course (NOT both).
    Placement tests have neither — they belong to no specific course.
    Validation in clean() enforces the right combination per kind.
    """

    class Kind(models.TextChoices):
        LESSON_QUIZ  = "lesson_quiz",  "Lesson quiz"
        COURSE_FINAL = "course_final", "Course final"
        PLACEMENT    = "placement",    "Placement test"

    kind = models.CharField(max_length=14, choices=Kind.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Optional scope. Exactly one of (lesson, course) is set for lesson_quiz
    # and course_final; both are null for placement tests.
    lesson = models.ForeignKey(
        "curriculum.Lesson",
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True,
        blank=True,
        help_text="Set for lesson_quiz; leave blank otherwise.",
    )
    course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True,
        blank=True,
        help_text="Set for course_final; leave blank otherwise.",
    )

    pass_threshold = models.PositiveSmallIntegerField(
        default=70,
        help_text="Percentage required to pass (0–100).",
    )
    randomize_questions = models.BooleanField(
        default=False,
        help_text="Shuffle question order for each attempt.",
    )
    time_limit_minutes = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Optional time limit. Blank = no limit.",
    )

    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "quiz"
        verbose_name_plural = "quizzes"

    def __str__(self):
        return f"{self.get_kind_display()}: {self.title}"

    def clean(self):
        # Scope rules per kind.
        if self.kind == self.Kind.LESSON_QUIZ:
            if not self.lesson_id or self.course_id:
                raise ValidationError(
                    "A lesson quiz must have a lesson and no course."
                )
        elif self.kind == self.Kind.COURSE_FINAL:
            if not self.course_id or self.lesson_id:
                raise ValidationError(
                    "A course final must have a course and no lesson."
                )
        elif self.kind == self.Kind.PLACEMENT:
            if self.lesson_id or self.course_id:
                raise ValidationError(
                    "A placement test must NOT belong to a lesson or course."
                )

        if not (0 <= self.pass_threshold <= 100):
            raise ValidationError(
                {"pass_threshold": "Must be between 0 and 100."}
            )


# =========================================================
# Question — one item in a quiz
# =========================================================
class Question(models.Model):
    """
    One question in a quiz.

    Kind decides which fields the player UI shows, and how grading works:
        mcq          -> one correct Choice (radio)
        multi_select -> one or more correct Choices (checkboxes)
        true_false   -> exactly two Choices ('True' and 'False'), one correct
        short_answer -> free text; manual grading by teacher

    `points` lets a question carry more weight than a default 1.
    `explanation` is shown to the student after submission, regardless
    of whether they got it right.
    """

    class Kind(models.TextChoices):
        MCQ          = "mcq",          "Multiple choice (one answer)"
        MULTI_SELECT = "multi_select", "Multiple choice (multiple answers)"
        TRUE_FALSE   = "true_false",   "True / false"
        SHORT_ANSWER = "short_answer", "Short answer (manual grade)"

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    order = models.PositiveSmallIntegerField()
    text = models.TextField(help_text="The question, in markdown or plain text.")
    kind = models.CharField(max_length=14, choices=Kind.choices)
    points = models.PositiveSmallIntegerField(default=1)
    explanation = models.TextField(
        blank=True,
        help_text="Shown after submission. Helps the student learn from mistakes.",
    )

    class Meta:
        ordering = ["quiz", "order"]
        constraints = [
            # Two questions in the same quiz can't share an order.
            models.UniqueConstraint(
                fields=["quiz", "order"],
                name="question_unique_order_per_quiz",
            ),
        ]
        verbose_name = "question"
        verbose_name_plural = "questions"

    def __str__(self):
        return f"{self.quiz.title} · {self.order}. {self.text[:60]}"


# =========================================================
# Choice — an option for an MCQ / multi / TF question
# =========================================================
class Choice(models.Model):
    """
    A selectable option attached to one Question.

    Not used for short_answer questions. The grader checks
    `is_correct=True` choices against the student's selected_choices.
    """

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
    )
    order = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=400)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["question", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["question", "order"],
                name="choice_unique_order_per_question",
            ),
        ]
        verbose_name = "choice"
        verbose_name_plural = "choices"

    def __str__(self):
        marker = " ✓" if self.is_correct else ""
        return f"{self.text}{marker}"


# =========================================================
# Submission — one student's attempt at one quiz
# =========================================================
class Submission(models.Model):
    """
    A single attempt. Re-takes get new rows; we never overwrite history.

    Lifecycle:
        in_progress  -> opened, not yet submitted
        submitted    -> answers locked, grade computed (or pending if any
                        short-answer questions need a teacher)
        graded       -> all answers graded; pass/fail finalised

    `score` is a percentage 0–100 (computed) once the submission is graded.
    `passed` is denormalised from score >= quiz.pass_threshold for fast
    queries ("who passed B1 final this month").
    """

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED   = "submitted",   "Submitted (awaiting grade)"
        GRADED      = "graded",      "Graded"

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.PROTECT,  # never lose submission history
        related_name="submissions",
    )
    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,  # student gone -> their attempts gone
        related_name="submissions",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    score = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Percentage 0–100, computed by the grader.",
    )
    passed = models.BooleanField(
        null=True, blank=True,
        help_text="Denormalised: score >= quiz.pass_threshold.",
    )

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "submission"
        verbose_name_plural = "submissions"

    def __str__(self):
        return f"{self.student} · {self.quiz.title} ({self.status})"


# =========================================================
# Answer — one student's response to one Question
# =========================================================
class Answer(models.Model):
    """
    One student's answer to one question within one Submission.

    `selected_choices` is the M2M for mcq / multi_select / true_false.
    `text_answer` is for short_answer.
    `is_correct` and `points_awarded` are filled by the grader (auto for
    Choice-based, manual for short_answer).

    Constraint: one Answer per (submission, question). Re-answering the
    same question within an attempt updates the existing row.
    """

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,  # never silently delete an answered question
        related_name="answers",
    )
    selected_choices = models.ManyToManyField(
        Choice,
        blank=True,
        related_name="selected_in_answers",
    )
    text_answer = models.TextField(blank=True)

    is_correct = models.BooleanField(null=True, blank=True)
    points_awarded = models.PositiveSmallIntegerField(null=True, blank=True)

    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["submission", "question__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["submission", "question"],
                name="answer_unique_submission_question",
            ),
        ]
        verbose_name = "answer"
        verbose_name_plural = "answers"

    def __str__(self):
        return f"Q{self.question.order} of {self.submission}"

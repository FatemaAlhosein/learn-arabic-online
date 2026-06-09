"""
assessments/admin.py

Admin for the quiz tooling. Inlines so a teacher can edit a whole quiz
on one page: Question rows on QuizAdmin, Choice rows on QuestionAdmin.
"""

from django.contrib import admin, messages

from .models import Answer, Choice, Question, Quiz, Submission
from .services import grade_submission


# =========================================================
# Inlines
# =========================================================
class QuestionInline(admin.TabularInline):
    """Edit a quiz's questions inline on the quiz page."""

    model = Question
    extra = 0
    fields = ("order", "kind", "text", "points")
    show_change_link = True
    ordering = ("order",)


class ChoiceInline(admin.TabularInline):
    """Edit a question's choices inline on the question page."""

    model = Choice
    extra = 0
    fields = ("order", "text", "is_correct")
    ordering = ("order",)


class AnswerInline(admin.TabularInline):
    """Read-only listing of answers on a Submission page."""

    model = Answer
    extra = 0
    can_delete = False
    fields = ("question", "text_answer", "is_correct", "points_awarded")
    readonly_fields = fields
    ordering = ("question__order",)


# =========================================================
# Quiz
# =========================================================
@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "lesson", "course", "pass_threshold",
                    "is_published", "created_at")
    list_filter = ("kind", "is_published")
    search_fields = ("title", "description", "course__title", "lesson__title")
    autocomplete_fields = ("lesson", "course")
    readonly_fields = ("created_at", "updated_at")
    inlines = [QuestionInline]


# =========================================================
# Question
# =========================================================
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "kind", "points",
                    "short_text")
    list_filter = ("kind", "quiz")
    search_fields = ("text", "quiz__title")
    autocomplete_fields = ("quiz",)
    inlines = [ChoiceInline]
    ordering = ("quiz", "order")

    def short_text(self, obj):
        return (obj.text[:80] + "…") if len(obj.text) > 80 else obj.text
    short_text.short_description = "text"


# =========================================================
# Submission
# =========================================================
@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("student", "quiz", "status", "score", "passed",
                    "started_at", "submitted_at")
    list_filter = ("status", "passed", "quiz__kind")
    search_fields = ("student__user__email", "quiz__title")
    autocomplete_fields = ("student", "quiz")
    readonly_fields = ("started_at", "submitted_at", "graded_at",
                       "score", "passed")
    inlines = [AnswerInline]

    actions = ["regrade_selected"]

    @admin.action(description="Re-run the auto-grader on selected submissions")
    def regrade_selected(self, request, queryset):
        """
        Useful after a teacher edits short-answer points on individual
        Answer rows — pushes the new totals back onto the Submission.
        """
        n = 0
        for submission in queryset:
            grade_submission(submission)
            n += 1
        self.message_user(
            request,
            f"Re-graded {n} submission{'s' if n != 1 else ''}.",
            level=messages.SUCCESS,
        )


# =========================================================
# Answer (rarely viewed standalone, but registered for completeness)
# =========================================================
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("submission", "question", "is_correct", "points_awarded")
    list_filter = ("is_correct",)
    search_fields = ("submission__student__user__email", "question__text")
    autocomplete_fields = ("submission", "question")

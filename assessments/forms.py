"""
assessments/forms.py

Teacher-facing forms for creating and editing quizzes and questions.
"""

from django import forms
from django.forms import inlineformset_factory

from .models import Choice, Question, Quiz


# =========================================================
# Quiz form
# =========================================================
class QuizForm(forms.ModelForm):
    """
    Create or edit a quiz. Teachers cannot create placement tests
    (those are admin-only) so the kind choices are restricted.
    """

    TEACHER_KIND_CHOICES = [
        (Quiz.Kind.LESSON_QUIZ,  "Lesson quiz — attached to a single lesson"),
        (Quiz.Kind.COURSE_FINAL, "Course final — attached to a whole course"),
    ]

    class Meta:
        model = Quiz
        fields = [
            "title", "kind", "lesson", "course",
            "pass_threshold", "time_limit_minutes",
            "randomize_questions", "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Lesson 1 vocabulary check",
            }),
            "kind": forms.Select(attrs={"class": "form-select", "id": "id_kind"}),
            "lesson": forms.Select(attrs={"class": "form-select"}),
            "course": forms.Select(attrs={"class": "form-select"}),
            "pass_threshold": forms.NumberInput(attrs={
                "class": "form-control", "min": 0, "max": 100,
            }),
            "time_limit_minutes": forms.NumberInput(attrs={
                "class": "form-control", "min": 1,
                "placeholder": "Leave blank for no limit",
            }),
            "randomize_questions": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "is_published": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "time_limit_minutes": "Time limit (minutes)",
            "randomize_questions": "Randomise question order for each attempt",
            "is_published": "Published (visible to students)",
        }
        help_texts = {
            "pass_threshold": "Percentage needed to pass (0–100). Default: 70.",
            "lesson": "Required for lesson quizzes.",
            "course": "Required for course finals.",
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].choices = self.TEACHER_KIND_CHOICES
        # Restrict lesson/course dropdowns to the teacher's own content.
        if teacher:
            from curriculum.models import Course, Lesson
            teacher_courses = Course.objects.filter(teacher=teacher)
            self.fields["lesson"].queryset = Lesson.objects.filter(
                course__teacher=teacher
            ).select_related("course").order_by("course__title", "order")
            self.fields["course"].queryset = teacher_courses.order_by("title")
        self.fields["lesson"].required = False
        self.fields["course"].required = False
        self.fields["lesson"].empty_label = "— Select a lesson —"
        self.fields["course"].empty_label = "— Select a course —"


# =========================================================
# Question form
# =========================================================
class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["order", "text", "kind", "points", "explanation"]
        widgets = {
            "order": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "text": forms.Textarea(attrs={
                "class": "form-control", "rows": 3,
                "placeholder": "Write the question here…",
            }),
            "kind": forms.Select(attrs={
                "class": "form-select", "id": "id_q_kind",
            }),
            "points": forms.NumberInput(attrs={
                "class": "form-control", "min": 1,
            }),
            "explanation": forms.Textarea(attrs={
                "class": "form-control", "rows": 2,
                "placeholder": "Optional explanation shown after the student answers…",
            }),
        }
        labels = {
            "text": "Question text",
            "explanation": "Explanation (shown after submission)",
        }


# =========================================================
# Choice form + formset
# =========================================================
class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ["order", "text", "is_correct"]
        widgets = {
            "order": forms.NumberInput(attrs={
                "class": "form-control form-control-sm", "min": 1,
                "style": "width:4rem;",
            }),
            "text": forms.TextInput(attrs={
                "class": "form-control form-control-sm",
                "placeholder": "Choice text…",
            }),
            "is_correct": forms.CheckboxInput(
                attrs={"class": "form-check-input mt-2"}
            ),
        }


ChoiceFormSet = inlineformset_factory(
    Question,
    Choice,
    form=ChoiceForm,
    extra=4,
    max_num=8,
    can_delete=True,
)

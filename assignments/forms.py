"""
assignments/forms.py

Teacher: AssignmentForm
Student: SubmissionForm
Teacher grading: GradeForm
"""

from django import forms
from django.utils import timezone

from .models import Assignment, AssignmentSubmission


class AssignmentForm(forms.ModelForm):
    """Teacher creates or edits an assignment."""

    class Meta:
        model = Assignment
        fields = [
            "title", "description", "instructions",
            "lesson", "course",
            "due_date", "max_score",
            "allow_text_response", "allow_file_upload",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Write a short paragraph using today's vocabulary",
            }),
            "description": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "One-line summary shown in the lesson page…",
            }),
            "instructions": forms.Textarea(attrs={
                "class": "form-control", "rows": 6,
                "placeholder": "Full instructions for the student. Markdown supported.",
            }),
            "lesson": forms.Select(attrs={"class": "form-select", "id": "id_a_lesson"}),
            "course": forms.Select(attrs={"class": "form-select", "id": "id_a_course"}),
            "due_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "max_score": forms.NumberInput(attrs={
                "class": "form-control", "min": 1,
            }),
            "allow_text_response": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "allow_file_upload": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "is_published": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "description": "Brief summary (shown in the lesson/course page)",
            "instructions": "Full instructions",
            "allow_text_response": "Allow written text response",
            "allow_file_upload": "Allow file attachment (PDF, Word, image…)",
            "is_published": "Published (visible to enrolled students)",
            "due_date": "Due date & time (optional)",
        }

    def __init__(self, *args, teacher=None, lesson=None, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher:
            from curriculum.models import Course, Lesson
            self.fields["lesson"].queryset = (
                Lesson.objects.filter(course__teacher=teacher)
                .select_related("course")
                .order_by("course__title", "order")
            )
            self.fields["course"].queryset = (
                Course.objects.filter(teacher=teacher).order_by("title")
            )
        self.fields["lesson"].required = False
        self.fields["course"].required = False
        self.fields["lesson"].empty_label = "— Select a lesson —"
        self.fields["course"].empty_label = "— Select a course —"
        # Pre-fill from context.
        if lesson:
            self.fields["lesson"].initial = lesson
        if course:
            self.fields["course"].initial = course


class SubmissionForm(forms.ModelForm):
    """Student submits an assignment."""

    class Meta:
        model = AssignmentSubmission
        fields = ["text_response", "file"]
        widgets = {
            "text_response": forms.Textarea(attrs={
                "class": "form-control", "rows": 8,
                "placeholder": "Type your answer here…",
            }),
            "file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "text_response": "Your written response",
            "file": "Attach a file (PDF, Word, image…)",
        }


class GradeForm(forms.ModelForm):
    """Teacher grades a submission."""

    class Meta:
        model = AssignmentSubmission
        fields = ["score", "feedback"]
        widgets = {
            "score": forms.NumberInput(attrs={
                "class": "form-control", "min": 0,
            }),
            "feedback": forms.Textarea(attrs={
                "class": "form-control", "rows": 5,
                "placeholder": "Written feedback shown to the student…",
            }),
        }
        labels = {
            "score": "Score",
            "feedback": "Feedback for the student",
        }

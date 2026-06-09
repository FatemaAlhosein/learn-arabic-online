"""
curriculum/forms.py
--------------------
Forms for the teacher-facing course and lesson management UI.
These are NOT used in the Django admin (admin.py handles its own forms).
"""

from django import forms
from django.utils.text import slugify

from .models import Category, Course, Lesson, Level


# =========================================================
# Course form — create or edit a course
# =========================================================
class CourseForm(forms.ModelForm):
    """
    Teacher-facing form for creating or editing a course.
    The `teacher` field is injected by the view (not shown to the user).
    """

    class Meta:
        model = Course
        fields = [
            "title",
            "description",
            "level",
            "category",
            "track",
            "thumbnail",
            "is_published",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Arabic for Complete Beginners",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Brief description shown in the course catalogue…",
            }),
            "level": forms.Select(attrs={"class": "form-select"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "track": forms.Select(attrs={"class": "form-select"}),
            "thumbnail": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "is_published": "Publish immediately (visible in the course catalogue)",
        }
        help_texts = {
            "level": "Leave blank for an open course anyone can join.",
            "thumbnail": "Optional. JPG/PNG, ideally 1280×720.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active categories.
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        # Level is optional — add a blank option.
        self.fields["level"].required = False
        self.fields["level"].empty_label = "— No level (open course) —"

    def save(self, commit=True, teacher=None):
        course = super().save(commit=False)
        # Auto-generate slug from title if new.
        if not course.slug:
            base = slugify(course.title)
            slug = base
            n = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            course.slug = slug
        if teacher:
            course.teacher = teacher
        if commit:
            course.save()
        return course


# =========================================================
# Lesson form — create or edit a lesson
# =========================================================
class LessonForm(forms.ModelForm):
    """
    Teacher-facing form for creating or editing a lesson.
    The `course` field is injected by the view (not shown to the user).
    `body_markdown` gets a live-preview widget via JS in the template.
    """

    class Meta:
        model = Lesson
        fields = [
            "title",
            "order",
            "body_markdown",
            "primary_video_url",
            "video_file",
            "duration_minutes",
            "is_free_preview",
        ]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Lesson 1 – The Arabic Alphabet",
            }),
            "order": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),
            # EasyMDE replaces this textarea with its own rich editor UI.
            # The placeholder is overridden by EasyMDE's own placeholder option,
            # but we keep a minimal one here as a fallback for no-JS environments.
            "body_markdown": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 20,
            }),
            "primary_video_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://www.youtube.com/embed/…",
            }),
            "video_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "duration_minutes": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
                "placeholder": "e.g. 15",
            }),
            "is_free_preview": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "is_free_preview": "Free preview (visible without enrolment)",
            "primary_video_url": "Video embed URL (YouTube / Vimeo)",
            "video_file": "Or upload a video file (MP4 / WebM)",
            "duration_minutes": "Duration (minutes)",
        }
        help_texts = {
            "primary_video_url": "Use the embed URL, e.g. youtube.com/embed/VIDEO_ID",
            "video_file": "Takes precedence over the embed URL if both are set.",
            "body_markdown": "Supports headers, bold, italics, tables, code blocks, and blockquotes.",
        }

    def save(self, commit=True, course=None):
        lesson = super().save(commit=False)
        if course:
            lesson.course = course
        # Auto-generate slug from title if new.
        if not lesson.slug:
            base = slugify(lesson.title)
            slug = base
            n = 1
            while Lesson.objects.filter(course=lesson.course, slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            lesson.slug = slug
        if commit:
            lesson.save()
        return lesson

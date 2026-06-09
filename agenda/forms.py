from django import forms
from .models import AgendaItem, ClassSchedule


class AgendaItemForm(forms.ModelForm):
    class Meta:
        model  = AgendaItem
        fields = ["course", "kind", "title", "description", "date", "due_time",
                  "linked_lesson", "linked_assignment"]
        widgets = {
            "course":      forms.Select(attrs={"class": "form-select"}),
            "kind":        forms.Select(attrs={"class": "form-select"}),
            "title":       forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Homework: write 5 sentences"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "date":        forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "due_time":    forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "linked_lesson":     forms.Select(attrs={"class": "form-select"}),
            "linked_assignment": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "due_time":          "Due time (optional)",
            "linked_lesson":     "Link to lesson (optional)",
            "linked_assignment": "Link to assignment (optional)",
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher:
            from curriculum.models import Course, Lesson
            from assignments.models import Assignment
            courses = Course.objects.filter(teacher=teacher, is_published=True).order_by("title")
            self.fields["course"].queryset = courses
            self.fields["linked_lesson"].queryset = (
                Lesson.objects.filter(course__teacher=teacher).select_related("course").order_by("course__title", "order")
            )
            self.fields["linked_assignment"].queryset = (
                Assignment.objects.filter(created_by=teacher).order_by("-created_at")
            )
        self.fields["linked_lesson"].required     = False
        self.fields["linked_assignment"].required = False
        self.fields["linked_lesson"].empty_label     = "— None —"
        self.fields["linked_assignment"].empty_label = "— None —"
        self.fields["due_time"].required = False


class ClassScheduleForm(forms.ModelForm):
    class Meta:
        model  = ClassSchedule
        fields = ["course", "day_of_week", "start_time", "end_time", "location", "note"]
        widgets = {
            "course":      forms.Select(attrs={"class": "form-select"}),
            "day_of_week": forms.Select(attrs={"class": "form-select"}),
            "start_time":  forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "end_time":    forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "location":    forms.TextInput(attrs={"class": "form-control", "placeholder": "Room 3 / Zoom / Online"}),
            "note":        forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional note"}),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher:
            from curriculum.models import Course
            self.fields["course"].queryset = Course.objects.filter(
                teacher=teacher, is_published=True
            ).order_by("title")
        self.fields["location"].required = False
        self.fields["note"].required     = False

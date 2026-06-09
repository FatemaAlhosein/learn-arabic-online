"""
flashcards/forms.py

Teacher-facing forms for creating and editing flashcard decks and cards.
"""

from django import forms

from .models import Flashcard, FlashcardDeck


class DeckForm(forms.ModelForm):
    class Meta:
        model = FlashcardDeck
        fields = ["lesson", "title", "description", "is_published"]
        widgets = {
            "lesson": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. Lesson 1 Vocabulary",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control", "rows": 2,
                "placeholder": "Optional brief description…",
            }),
            "is_published": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "is_published": "Published (visible to students)",
        }

    def __init__(self, *args, teacher=None, lesson=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher:
            from curriculum.models import Lesson
            self.fields["lesson"].queryset = (
                Lesson.objects.filter(course__teacher=teacher)
                .select_related("course")
                .order_by("course__title", "order")
            )
        if lesson:
            self.fields["lesson"].initial = lesson
        self.fields["lesson"].empty_label = "— Select a lesson —"


class CardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = ["order", "front", "back", "front_lang", "back_lang",
                  "audio", "notes"]
        widgets = {
            "order": forms.NumberInput(attrs={
                "class": "form-control", "min": 1,
            }),
            "front": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Arabic word or phrase (front side)",
                "dir": "auto",
            }),
            "back": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "English translation (back side)",
            }),
            "front_lang": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "ar",
            }),
            "back_lang": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "en",
            }),
            "audio": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={
                "class": "form-control", "rows": 2,
                "placeholder": "Optional notes, grammar tip, or example sentence…",
            }),
        }
        labels = {
            "front": "Front (Arabic)",
            "back": "Back (translation)",
            "front_lang": "Front language code",
            "back_lang": "Back language code",
            "audio": "Pronunciation audio (MP3/OGG)",
        }
        help_texts = {
            "front_lang": "ISO code, e.g. 'ar' for Arabic.",
            "back_lang": "ISO code, e.g. 'en' for English.",
        }

"""
games/forms.py
Forms for teacher-facing game content management.
"""
import json

from django import forms
from django.core.exceptions import ValidationError

from .models import GameQuestion, VocabWord


class VocabWordForm(forms.ModelForm):
    """
    Teacher-friendly form for adding / editing a vocabulary word.
    letters and context_forms are rendered as plain text inputs
    (comma-separated) instead of raw JSON so teachers don't need
    to type square brackets.
    """

    letters_input = forms.CharField(
        required=False,
        label="Letter tiles (Word Builder)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "ك, ت, ا, ب",
            "dir": "rtl",
        }),
        help_text="Comma-separated individual letters, e.g.  ك, ت, ا, ب",
    )
    context_forms_input = forms.CharField(
        required=False,
        label="Contextual shapes (Word Builder)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "كـ, ـتـ, ـا, ب",
            "dir": "rtl",
        }),
        help_text="Comma-separated contextual forms, e.g.  كـ, ـتـ, ـا, ب",
    )
    wrong_choices_input = forms.CharField(
        required=False,
        label="Wrong choices (Missing Letter game)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "ن, م",
            "dir": "rtl",
        }),
        help_text="Exactly 2 wrong letter options, comma-separated",
    )

    class Meta:
        model = VocabWord
        fields = [
            "arabic", "english", "emoji", "phonetic",
            "missing_index",
            "level", "course", "is_active",
        ]
        widgets = {
            "arabic":   forms.TextInput(attrs={"class": "form-control", "dir": "rtl", "placeholder": "كِتَاب"}),
            "english":  forms.TextInput(attrs={"class": "form-control", "placeholder": "Book"}),
            "emoji":    forms.TextInput(attrs={"class": "form-control", "placeholder": "📚", "maxlength": 10}),
            "phonetic": forms.TextInput(attrs={"class": "form-control", "placeholder": "kitāb"}),
            "missing_index": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "level":   forms.Select(attrs={"class": "form-select"}),
            "course":  forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-fill the comma-separated helpers from existing JSON data
        if self.instance.pk:
            self.fields["letters_input"].initial = ", ".join(self.instance.letters)
            self.fields["context_forms_input"].initial = ", ".join(self.instance.context_forms)
            self.fields["wrong_choices_input"].initial = ", ".join(self.instance.wrong_choices)

    def _split(self, raw):
        """Split a comma-separated string into a clean list, strip whitespace."""
        if not raw or not raw.strip():
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    def clean_wrong_choices_input(self):
        raw = self.cleaned_data.get("wrong_choices_input", "")
        items = self._split(raw)
        if items and len(items) != 2:
            raise ValidationError("Please enter exactly 2 wrong choices separated by a comma.")
        return items

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.letters       = self._split(self.cleaned_data.get("letters_input", ""))
        obj.context_forms = self._split(self.cleaned_data.get("context_forms_input", ""))
        obj.wrong_choices = self.cleaned_data.get("wrong_choices_input", [])
        if commit:
            obj.save()
        return obj


class GameQuestionForm(forms.ModelForm):
    """
    Form for Sentence Builder and True-or-False questions.
    word_tokens is entered as comma-separated Arabic words.
    """

    word_tokens_input = forms.CharField(
        required=False,
        label="Word tiles (Sentence Builder only)",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "أنا, أذهب, إلى, المدرسة",
            "dir": "rtl",
        }),
        help_text="Arabic words in correct order, comma-separated. Tiles will be shuffled for the student.",
    )

    class Meta:
        model = GameQuestion
        fields = [
            "game_type", "arabic_sentence", "english_sentence",
            "emoji", "is_true",
            "level", "course", "is_active",
        ]
        widgets = {
            "game_type":        forms.Select(attrs={"class": "form-select", "id": "id_game_type"}),
            "arabic_sentence":  forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
            "english_sentence": forms.TextInput(attrs={"class": "form-control"}),
            "emoji":            forms.TextInput(attrs={"class": "form-control", "maxlength": 10}),
            "is_true":          forms.NullBooleanSelect(attrs={"class": "form-select", "id": "id_is_true"}),
            "level":   forms.Select(attrs={"class": "form-select"}),
            "course":  forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["word_tokens_input"].initial = ", ".join(self.instance.word_tokens)

    def save(self, commit=True):
        obj = super().save(commit=False)
        raw = self.cleaned_data.get("word_tokens_input", "")
        obj.word_tokens = [w.strip() for w in raw.split(",") if w.strip()] if raw.strip() else []
        if commit:
            obj.save()
        return obj

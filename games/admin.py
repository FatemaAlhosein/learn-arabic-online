"""
games/admin.py

Admin registration for VocabWord and GameQuestion.
Teachers and admins manage all game content from here.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import GameQuestion, VocabWord


# ─────────────────────────────────────────────────────────────
#  VocabWord
# ─────────────────────────────────────────────────────────────
@admin.register(VocabWord)
class VocabWordAdmin(admin.ModelAdmin):
    list_display  = ("arabic_display", "english", "emoji", "level", "course", "is_active", "created_at")
    list_filter   = ("level", "course", "is_active")
    search_fields = ("arabic", "english", "phonetic")
    readonly_fields = ("created_at", "updated_at", "created_by")
    list_editable  = ("is_active",)
    list_per_page  = 50

    fieldsets = (
        ("Content", {
            "fields": ("arabic", "english", "emoji", "phonetic"),
        }),
        ("Letter tiles (Word Builder)", {
            "classes": ("collapse",),
            "fields": ("letters", "context_forms"),
            "description": (
                "Fill these in if this word should appear in the Word Builder game. "
                'Example letters: ["ك","ت","ا","ب"]'
            ),
        }),
        ("Missing Letter", {
            "classes": ("collapse",),
            "fields": ("missing_index", "wrong_choices"),
            "description": (
                "Fill these in if this word should appear in the Missing Letter game. "
                "missing_index is 0-based. wrong_choices = 2 wrong options."
            ),
        }),
        ("Curriculum", {
            "fields": ("level", "course"),
        }),
        ("Status", {
            "fields": ("is_active", "created_by", "created_at", "updated_at"),
        }),
    )

    def arabic_display(self, obj):
        return format_html(
            '<span style="font-family:\'Cairo\',serif;font-size:1.2em;direction:rtl;">{}</span>',
            obj.arabic,
        )
    arabic_display.short_description = "Arabic"
    arabic_display.admin_order_field = "arabic"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# ─────────────────────────────────────────────────────────────
#  GameQuestion
# ─────────────────────────────────────────────────────────────
@admin.register(GameQuestion)
class GameQuestionAdmin(admin.ModelAdmin):
    list_display  = ("arabic_display", "game_type", "english_sentence", "emoji", "level", "is_active")
    list_filter   = ("game_type", "level", "course", "is_active")
    search_fields = ("arabic_sentence", "english_sentence")
    list_editable  = ("is_active",)
    readonly_fields = ("created_at", "created_by")
    list_per_page  = 50

    fieldsets = (
        ("Question", {
            "fields": ("game_type", "arabic_sentence", "english_sentence", "emoji"),
        }),
        ("Sentence Builder", {
            "classes": ("collapse",),
            "fields": ("word_tokens",),
            "description": (
                "Word tiles in the correct sentence order. "
                'Example: ["أنا","أذهب","إلى","المدرسة"]'
            ),
        }),
        ("True or False", {
            "classes": ("collapse",),
            "fields": ("is_true",),
        }),
        ("Curriculum", {
            "fields": ("level", "course"),
        }),
        ("Status", {
            "fields": ("is_active", "created_by", "created_at"),
        }),
    )

    def arabic_display(self, obj):
        return format_html(
            '<span style="font-family:\'Cairo\',serif;direction:rtl;">{}</span>',
            obj.arabic_sentence[:60],
        )
    arabic_display.short_description = "Arabic sentence"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


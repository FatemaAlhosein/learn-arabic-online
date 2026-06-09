"""
flashcards/admin.py

Inlines so a teacher can edit a whole deck on one page.
"""

from django.contrib import admin

from .models import Flashcard, FlashcardDeck, FlashcardReview


# =========================================================
# Inlines
# =========================================================
class FlashcardInline(admin.TabularInline):
    """Edit a deck's cards on the deck page."""

    model = Flashcard
    extra = 0
    fields = ("order", "front", "back", "front_lang", "back_lang", "audio")
    ordering = ("order",)


# =========================================================
# Deck admin
# =========================================================
@admin.register(FlashcardDeck)
class FlashcardDeckAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "card_count",
                    "is_published", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "description", "lesson__title")
    autocomplete_fields = ("lesson",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [FlashcardInline]

    def card_count(self, obj):
        return obj.cards.count()
    card_count.short_description = "cards"


# =========================================================
# Card admin (rarely used standalone, but registered)
# =========================================================
@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ("front", "back", "deck", "order")
    list_filter = ("deck",)
    search_fields = ("front", "back", "deck__title")
    autocomplete_fields = ("deck",)


# =========================================================
# Review admin
# =========================================================
@admin.register(FlashcardReview)
class FlashcardReviewAdmin(admin.ModelAdmin):
    list_display = ("student", "flashcard", "times_seen",
                    "times_correct", "streak", "is_mastered",
                    "last_seen_at")
    list_filter = ("is_mastered",)
    search_fields = ("student__user__email", "flashcard__front")
    autocomplete_fields = ("student", "flashcard")
    readonly_fields = ("last_seen_at", "last_correct_at")

"""URL patterns for flashcard study mode + teacher deck builder."""

from django.urls import path

from . import views


app_name = "flashcards"

urlpatterns = [
    # ── Student: study modes ──────────────────────────────────────────
    path("decks/<int:deck_id>/",
         views.deck_intro, name="deck_intro"),
    path("decks/<int:deck_id>/study/",
         views.study_session, name="study_session"),
    path("decks/<int:deck_id>/summary/",
         views.deck_summary, name="deck_summary"),
    path("decks/<int:deck_id>/match/",
         views.match_game, name="match_game"),
    path("decks/<int:deck_id>/sprint/",
         views.sprint_game, name="sprint_game"),

    # ── Teacher: deck builder ─────────────────────────────────────────
    path("decks/teach/new/",
         views.deck_create, name="deck_create"),
    path("decks/teach/<int:deck_id>/edit/",
         views.deck_edit, name="deck_edit"),
    path("decks/teach/<int:deck_id>/manage/",
         views.deck_manage, name="deck_manage"),
    path("decks/teach/<int:deck_id>/delete/",
         views.deck_delete, name="deck_delete"),

    # ── Teacher: card builder ─────────────────────────────────────────
    path("decks/teach/<int:deck_id>/cards/new/",
         views.card_create, name="card_create"),
    path("decks/teach/<int:deck_id>/cards/<int:card_id>/edit/",
         views.card_edit, name="card_edit"),
    path("decks/teach/<int:deck_id>/cards/<int:card_id>/delete/",
         views.card_delete, name="card_delete"),
]

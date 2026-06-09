"""URL patterns for the games section."""
from django.urls import path
from . import views

app_name = "games"

urlpatterns = [
    # ── Student game views ──────────────────────────────────
    path("",                  views.hub,              name="hub"),
    path("word-builder/",     views.word_builder,     name="word_builder"),
    path("match-pairs/",      views.match_pairs,      name="match_pairs"),
    path("sentence-builder/", views.sentence_builder, name="sentence_builder"),
    path("missing-letter/",   views.missing_letter,   name="missing_letter"),
    path("true-or-false/",    views.true_or_false,    name="true_or_false"),
    path("word-hunt/",        views.word_hunt,        name="word_hunt"),

    # ── Teacher: vocabulary management ─────────────────────
    path("teach/vocab/",                  views.vocab_list,   name="vocab_list"),
    path("teach/vocab/add/",             views.vocab_create, name="vocab_create"),
    path("teach/vocab/<int:word_id>/edit/",   views.vocab_edit,   name="vocab_edit"),
    path("teach/vocab/<int:word_id>/delete/", views.vocab_delete, name="vocab_delete"),

    # ── Teacher: game questions management ─────────────────
    path("teach/questions/",                        views.question_list,   name="question_list"),
    path("teach/questions/add/",                    views.question_create, name="question_create"),
    path("teach/questions/<int:question_id>/edit/", views.question_edit,   name="question_edit"),
    path("teach/questions/<int:question_id>/delete/", views.question_delete, name="question_delete"),
]

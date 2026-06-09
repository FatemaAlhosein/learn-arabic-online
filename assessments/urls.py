"""URL patterns for quiz player + teacher quiz builder."""

from django.urls import path

from . import views


app_name = "assessments"

urlpatterns = [
    # ── Student: quiz player ──────────────────────────────────────────
    path("quizzes/<int:quiz_id>/", views.quiz_intro, name="quiz_intro"),
    path("quizzes/<int:quiz_id>/start/", views.start_quiz, name="start_quiz"),
    path(
        "submissions/<int:submission_id>/q/<int:order>/",
        views.take_question,
        name="take_question",
    ),
    path(
        "submissions/<int:submission_id>/submit/",
        views.submit_quiz,
        name="submit_quiz",
    ),
    path(
        "submissions/<int:submission_id>/",
        views.submission_result,
        name="submission_result",
    ),

    # ── Teacher: quiz builder ─────────────────────────────────────────
    path("quizzes/teach/new/",
         views.quiz_create, name="quiz_create"),
    path("quizzes/teach/<int:quiz_id>/edit/",
         views.quiz_edit, name="quiz_edit"),
    path("quizzes/teach/<int:quiz_id>/manage/",
         views.quiz_manage, name="quiz_manage"),
    path("quizzes/teach/<int:quiz_id>/delete/",
         views.quiz_delete, name="quiz_delete"),

    # ── Teacher: question builder ─────────────────────────────────────
    path("quizzes/teach/<int:quiz_id>/questions/new/",
         views.question_create, name="question_create"),
    path("quizzes/teach/<int:quiz_id>/questions/<int:question_id>/edit/",
         views.question_edit, name="question_edit"),
    path("quizzes/teach/<int:quiz_id>/questions/<int:question_id>/delete/",
         views.question_delete, name="question_delete"),
]

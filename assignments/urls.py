"""URL patterns for the assignments app."""

from django.urls import path

from . import views

app_name = "assignments"

urlpatterns = [
    # ── Teacher ───────────────────────────────────────────────────────
    path("assignments/teach/new/",
         views.assignment_create, name="assignment_create"),
    path("assignments/teach/<int:assignment_id>/edit/",
         views.assignment_edit, name="assignment_edit"),
    path("assignments/teach/<int:assignment_id>/delete/",
         views.assignment_delete, name="assignment_delete"),
    path("assignments/teach/<int:assignment_id>/submissions/",
         views.submission_list, name="submission_list"),
    path("assignments/teach/<int:assignment_id>/submissions/<int:submission_id>/grade/",
         views.grade_submission, name="grade_submission"),

    # ── Student ───────────────────────────────────────────────────────
    path("assignments/<int:assignment_id>/",
         views.assignment_detail, name="assignment_detail"),
]

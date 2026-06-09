"""URL patterns for the public-facing curriculum pages + teacher authoring."""

from django.urls import path

from . import views


app_name = "curriculum"

urlpatterns = [
    # ── Teacher authoring — MUST come first so "teach" is never caught
    #    by the generic <slug:slug>/ pattern below.
    path("teach/new/",                    views.course_create,  name="course_create"),
    path("teach/<slug:slug>/edit/",       views.course_edit,    name="course_edit"),
    path("teach/<slug:slug>/manage/",     views.course_manage,  name="course_manage"),
    path("teach/<slug:slug>/lessons/new/",
         views.lesson_create, name="lesson_create"),
    path("teach/<slug:slug>/lessons/<slug:lesson_slug>/edit/",
         views.lesson_edit,   name="lesson_edit"),
    path("teach/<slug:slug>/lessons/<slug:lesson_slug>/delete/",
         views.lesson_delete, name="lesson_delete"),

    # ── Public catalogue ────────────────────────────────────────────────
    path("", views.course_list, name="course_list"),
    path("<slug:slug>/", views.course_detail, name="course_detail"),
    path("<slug:slug>/enrol/", views.enrol, name="enrol"),
    path(
        "<slug:slug>/lessons/<slug:lesson_slug>/",
        views.lesson_detail,
        name="lesson_detail",
    ),
    path(
        "<slug:slug>/lessons/<slug:lesson_slug>/complete/",
        views.complete_lesson,
        name="complete_lesson",
    ),
]
# NOTE: the public certificate page is wired in core/urls.py at
# /certificates/<code>/ so the URL is shareable without the /courses/ prefix.

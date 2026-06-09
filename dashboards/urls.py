"""URL patterns for the role-dispatching dashboard."""

from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Progress report — teacher / parent / admin views a student's full progress
    path("progress/<int:student_id>/", views.student_progress, name="student_progress"),
    # Student views their own progress
    path("progress/", views.student_progress, name="my_progress"),
]

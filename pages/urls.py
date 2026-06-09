"""URL patterns for cross-cutting pages."""

from django.urls import path

from .views import HomeView, ReadingPracticeView


urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("reading-practice/", ReadingPracticeView.as_view(), name="reading_practice"),
]

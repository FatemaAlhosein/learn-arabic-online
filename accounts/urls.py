"""
accounts/urls.py

Custom auth URLs. Mounted at /accounts/ alongside Django's built-in auth
URL set, so login/logout/password-reset are handled automatically.
"""

from django.urls import path

from .views import SignupView, link_child, profile_view

app_name = "accounts"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("profile/", profile_view, name="profile"),
    path("link-child/", link_child, name="link_child"),
]

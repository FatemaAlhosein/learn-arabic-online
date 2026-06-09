from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("",              views.notification_list, name="list"),
    path("mark-read/",    views.mark_all_read,     name="mark_all_read"),
    path("<int:pk>/read/", views.mark_one_read,    name="mark_one_read"),
]

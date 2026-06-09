from django.urls import path
from . import views

app_name = "agenda"

urlpatterns = [
    # Student
    path("agenda/",                          views.student_agenda,      name="student_agenda"),
    path("agenda/toggle/<int:item_id>/",     views.toggle_task,         name="toggle_task"),

    # Teacher
    path("agenda/teach/",                    views.teacher_agenda,      name="teacher_agenda"),
    path("agenda/teach/new/",                views.agenda_item_create,  name="item_create"),
    path("agenda/teach/<int:item_id>/edit/", views.agenda_item_edit,    name="item_edit"),
    path("agenda/teach/<int:item_id>/delete/", views.agenda_item_delete, name="item_delete"),
    path("agenda/teach/schedule/new/",       views.schedule_create,     name="schedule_create"),
    path("agenda/teach/schedule/<int:schedule_id>/delete/", views.schedule_delete, name="schedule_delete"),

    # Parent
    path("agenda/parent/",                   views.parent_agenda,       name="parent_agenda"),
]

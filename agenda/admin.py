from django.contrib import admin
from .models import AgendaItem, ClassSchedule, StudentTask


@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ["course", "get_day_of_week_display", "start_time", "end_time", "location"]
    list_filter  = ["course", "day_of_week"]


@admin.register(AgendaItem)
class AgendaItemAdmin(admin.ModelAdmin):
    list_display  = ["title", "course", "kind", "date", "due_time", "created_by"]
    list_filter   = ["kind", "course", "date"]
    search_fields = ["title", "description"]
    date_hierarchy = "date"


@admin.register(StudentTask)
class StudentTaskAdmin(admin.ModelAdmin):
    list_display = ["student", "agenda_item", "is_done", "done_at"]
    list_filter  = ["is_done"]

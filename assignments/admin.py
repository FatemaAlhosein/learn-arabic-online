from django.contrib import admin

from .models import Assignment, AssignmentSubmission


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["title", "created_by", "lesson", "course", "is_published", "due_date", "created_at"]
    list_filter = ["is_published", "created_by"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display = ["assignment", "student", "status", "score", "submitted_at", "graded_at"]
    list_filter = ["status"]
    readonly_fields = ["submitted_at", "graded_at"]

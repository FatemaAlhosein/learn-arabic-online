"""
curriculum/admin.py

Admin registrations for all curriculum models. Most of these are vanilla
ModelAdmins; the interesting bits are:

  - inlines so a course shows its lessons on the same page
  - autocomplete_fields for FKs to keep the admin fast on big tables
  - prepopulated_fields so slugs auto-fill from titles in the admin form
  - readonly fields for auto-managed timestamps and computed values
"""

from django.contrib import admin

from .models import (
    Category,
    Course,
    Enrollment,
    Lesson,
    LessonAttachment,
    LessonProgress,
    Level,
)


# =========================================================
# Inlines — child editors that appear on the parent's edit page
# =========================================================
class LessonInline(admin.TabularInline):
    """Edit a course's lessons inline on the course page."""

    model = Lesson
    extra = 0  # no blank rows by default; admin clicks "Add another lesson"
    fields = ("order", "title", "slug", "duration_minutes",
              "is_free_preview")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("order",)
    show_change_link = True  # link to the full lesson edit page


class LessonAttachmentInline(admin.TabularInline):
    """Edit a lesson's attachments inline on the lesson page."""

    model = LessonAttachment
    extra = 0
    fields = ("order", "kind", "title", "file", "external_url",
              "is_downloadable")


# =========================================================
# Level admin
# =========================================================
@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "order")
    list_editable = ("order",)
    ordering = ("order",)
    search_fields = ("code", "name")


# =========================================================
# Category admin
# =========================================================
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at",)


# =========================================================
# Course admin
# =========================================================
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "category", "track", "teacher",
                    "is_published", "created_at")
    list_filter = ("is_published", "track", "level", "category")
    search_fields = ("title", "slug", "teacher__email")
    autocomplete_fields = ("teacher", "level", "category")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [LessonInline]


# =========================================================
# Lesson admin
# =========================================================
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("course", "order", "title", "is_free_preview",
                    "duration_minutes")
    list_filter = ("is_free_preview", "course")
    search_fields = ("title", "course__title")
    autocomplete_fields = ("course",)
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    inlines = [LessonAttachmentInline]
    ordering = ("course", "order")


# =========================================================
# LessonAttachment admin
# =========================================================
@admin.register(LessonAttachment)
class LessonAttachmentAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "kind", "is_downloadable",
                    "size_bytes", "created_at")
    list_filter = ("kind", "is_downloadable")
    search_fields = ("title", "lesson__title")
    autocomplete_fields = ("lesson",)
    readonly_fields = ("size_bytes", "created_at")


# =========================================================
# Enrollment admin
# =========================================================
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "started_at",
                    "completed_at")
    list_filter = ("status", "course")
    search_fields = ("student__user__email", "course__title")
    autocomplete_fields = ("student", "course")
    readonly_fields = ("started_at",)


# =========================================================
# LessonProgress admin
# =========================================================
@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "lesson", "status",
                    "last_viewed_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("enrollment__student__user__email",
                     "lesson__title")
    autocomplete_fields = ("enrollment", "lesson")

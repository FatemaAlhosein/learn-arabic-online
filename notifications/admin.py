from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("recipient", "kind", "short_message", "is_read", "created_at")
    list_filter   = ("kind", "is_read")
    search_fields = ("recipient__email", "message")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

    @admin.display(description="Message")
    def short_message(self, obj):
        return obj.message[:80]

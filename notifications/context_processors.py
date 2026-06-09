"""
notifications/context_processors.py

Injects `unread_notification_count` into every template context so the
navbar bell can show a badge without every view passing it manually.

Register in settings:
    TEMPLATES[0]["OPTIONS"]["context_processors"] += [
        "notifications.context_processors.unread_count",
    ]
"""

from .models import Notification


def unread_count(request):
    """Return unread notification count for the logged-in user."""
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0}
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()
    return {"unread_notification_count": count}

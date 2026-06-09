"""
notifications/views.py

  GET  /notifications/          → list all notifications (paginated)
  POST /notifications/mark-read/ → mark all as read (AJAX or form POST)
  POST /notifications/<id>/read/ → mark one notification as read
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    """Paginated list of the logged-in user's notifications."""
    notifications = (
        Notification.objects
        .filter(recipient=request.user)
        .order_by("-created_at")
    )

    unread_count = notifications.filter(is_read=False).count()

    # Mark all as read when the page is opened
    notifications.filter(is_read=False).update(is_read=True)

    return render(request, "notifications/list.html", {
        "notifications": notifications[:60],   # last 60
        "unread_count": unread_count,           # count BEFORE marking read
    })


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    return redirect("notifications:list")


@login_required
@require_POST
def mark_one_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True})
    if n.link:
        return redirect(n.link)
    return redirect("notifications:list")

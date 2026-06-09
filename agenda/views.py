"""
agenda/views.py

  student_agenda   — student's combined weekly agenda
  teacher_agenda   — teacher posts / manages agenda items & schedule
  agenda_item_create / edit / delete
  schedule_create / delete
  toggle_task      — AJAX: student marks an item done/undone
  parent_agenda    — parent sees child's agenda
"""

import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AgendaItem, ClassSchedule, StudentTask


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _week_bounds(date):
    """Return (monday, sunday) for the week containing date."""
    monday = date - datetime.timedelta(days=date.weekday())
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday


def _get_week_offset(request):
    try:
        return int(request.GET.get("w", 0))
    except (ValueError, TypeError):
        return 0


# ──────────────────────────────────────────────
# Student agenda
# ──────────────────────────────────────────────

@login_required
def student_agenda(request):
    if not request.user.is_student:
        return HttpResponseForbidden("Students only.")

    student = getattr(request.user, "student_profile", None)
    if not student:
        messages.warning(request, "Student profile not found.")
        return HttpResponseRedirect(reverse("dashboard"))

    offset = _get_week_offset(request)
    today  = timezone.localdate()
    target = today + datetime.timedelta(weeks=offset)
    monday, sunday = _week_bounds(target)

    # All courses this student is actively enrolled in.
    from curriculum.models import Enrollment
    enrolled_course_ids = list(
        Enrollment.objects.filter(student=student, status=Enrollment.Status.ACTIVE)
        .values_list("course_id", flat=True)
    )

    # Agenda items for this week across all enrolled courses.
    items = AgendaItem.objects.filter(
        course_id__in=enrolled_course_ids,
        date__range=(monday, sunday),
    ).select_related("course", "linked_lesson", "linked_assignment").order_by("date", "due_time")

    # Student's task records for these items.
    task_map = {}
    if items:
        tasks = StudentTask.objects.filter(
            student=student, agenda_item__in=items
        )
        task_map = {t.agenda_item_id: t for t in tasks}

    # Class schedule entries for enrolled courses.
    schedule = ClassSchedule.objects.filter(
        course_id__in=enrolled_course_ids
    ).select_related("course").order_by("day_of_week", "start_time")

    # Group items by date for the weekly grid.
    days = []
    for i in range(7):
        day_date = monday + datetime.timedelta(days=i)
        day_items = [item for item in items if item.date == day_date]
        # Attach task status to each item.
        for item in day_items:
            item.student_task = task_map.get(item.id)
        # Class schedule for this day.
        day_schedule = [s for s in schedule if s.day_of_week == i]
        days.append({
            "date": day_date,
            "is_today": day_date == today,
            "items": day_items,
            "schedule": day_schedule,
        })

    return render(request, "agenda/student_agenda.html", {
        "days": days,
        "monday": monday,
        "sunday": sunday,
        "today": today,
        "offset": offset,
        "prev_offset": offset - 1,
        "next_offset": offset + 1,
    })


# ──────────────────────────────────────────────
# Toggle task done/undone (AJAX POST)
# ──────────────────────────────────────────────

@login_required
@require_POST
def toggle_task(request, item_id):
    if not request.user.is_student:
        return JsonResponse({"error": "Students only."}, status=403)

    student = getattr(request.user, "student_profile", None)
    if not student:
        return JsonResponse({"error": "No student profile."}, status=400)

    item = get_object_or_404(AgendaItem, pk=item_id)

    task, _ = StudentTask.objects.get_or_create(
        agenda_item=item, student=student
    )
    task.is_done = not task.is_done
    task.done_at = timezone.now() if task.is_done else None
    task.save()

    return JsonResponse({"is_done": task.is_done})


# ──────────────────────────────────────────────
# Teacher agenda management
# ──────────────────────────────────────────────

@login_required
def teacher_agenda(request):
    from accounts.models import User
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    offset = _get_week_offset(request)
    today  = timezone.localdate()
    target = today + datetime.timedelta(weeks=offset)
    monday, sunday = _week_bounds(target)

    from curriculum.models import Course
    courses = Course.objects.filter(teacher=request.user, is_published=True).order_by("title")

    # Filter by course if requested.
    course_filter_id = request.GET.get("course")
    if course_filter_id:
        items = AgendaItem.objects.filter(
            course__teacher=request.user,
            course_id=course_filter_id,
            date__range=(monday, sunday),
        )
        schedule = ClassSchedule.objects.filter(
            course__teacher=request.user,
            course_id=course_filter_id,
        )
    else:
        items = AgendaItem.objects.filter(
            course__teacher=request.user,
            date__range=(monday, sunday),
        )
        schedule = ClassSchedule.objects.filter(
            course__teacher=request.user,
        )

    items    = items.select_related("course").order_by("date", "due_time")
    schedule = schedule.select_related("course").order_by("day_of_week", "start_time")

    # Group by day.
    days = []
    for i in range(7):
        day_date = monday + datetime.timedelta(days=i)
        day_items    = [it for it in items    if it.date == day_date]
        day_schedule = [s  for s  in schedule if s.day_of_week == i]
        days.append({
            "date": day_date,
            "is_today": day_date == today,
            "items": day_items,
            "schedule": day_schedule,
        })

    return render(request, "agenda/teacher_agenda.html", {
        "days": days,
        "monday": monday,
        "sunday": sunday,
        "today": today,
        "offset": offset,
        "prev_offset": offset - 1,
        "next_offset": offset + 1,
        "courses": courses,
        "course_filter_id": course_filter_id,
    })


# ──────────────────────────────────────────────
# Agenda item create / edit / delete
# ──────────────────────────────────────────────

@login_required
def agenda_item_create(request):
    from accounts.models import User
    from .forms import AgendaItemForm
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    initial = {}
    if d := request.GET.get("date"):
        try:
            initial["date"] = datetime.date.fromisoformat(d)
        except ValueError:
            pass
    if c := request.GET.get("course"):
        initial["course"] = c

    if request.method == "POST":
        form = AgendaItemForm(request.POST, teacher=request.user)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            messages.success(request, f'"{item.title}" added to agenda.')
            w = request.POST.get("week_offset", "0")
            return HttpResponseRedirect(reverse("agenda:teacher_agenda") + f"?w={w}")
    else:
        form = AgendaItemForm(teacher=request.user, initial=initial)

    return render(request, "agenda/item_form.html", {
        "form": form,
        "mode": "create",
        "week_offset": request.GET.get("w", "0"),
    })


@login_required
def agenda_item_edit(request, item_id):
    from accounts.models import User
    from .forms import AgendaItemForm
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    item = get_object_or_404(AgendaItem, pk=item_id, course__teacher=request.user)

    if request.method == "POST":
        form = AgendaItemForm(request.POST, instance=item, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Agenda item updated.")
            w = request.POST.get("week_offset", "0")
            return HttpResponseRedirect(reverse("agenda:teacher_agenda") + f"?w={w}")
    else:
        form = AgendaItemForm(instance=item, teacher=request.user)

    return render(request, "agenda/item_form.html", {
        "form": form,
        "item": item,
        "mode": "edit",
        "week_offset": request.GET.get("w", "0"),
    })


@login_required
@require_POST
def agenda_item_delete(request, item_id):
    from accounts.models import User
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    item = get_object_or_404(AgendaItem, pk=item_id, course__teacher=request.user)
    w = request.POST.get("week_offset", "0")
    item.delete()
    messages.success(request, "Agenda item deleted.")
    return HttpResponseRedirect(reverse("agenda:teacher_agenda") + f"?w={w}")


# ──────────────────────────────────────────────
# Class schedule create / delete
# ──────────────────────────────────────────────

@login_required
def schedule_create(request):
    from accounts.models import User
    from .forms import ClassScheduleForm
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    if request.method == "POST":
        form = ClassScheduleForm(request.POST, teacher=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            messages.success(request, "Class time added.")
            return HttpResponseRedirect(reverse("agenda:teacher_agenda"))
    else:
        form = ClassScheduleForm(teacher=request.user)

    return render(request, "agenda/schedule_form.html", {"form": form})


@login_required
@require_POST
def schedule_delete(request, schedule_id):
    from accounts.models import User
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    entry = get_object_or_404(ClassSchedule, pk=schedule_id, course__teacher=request.user)
    entry.delete()
    messages.success(request, "Class time removed.")
    return HttpResponseRedirect(reverse("agenda:teacher_agenda"))


# ──────────────────────────────────────────────
# Parent view — child's agenda
# ──────────────────────────────────────────────

@login_required
def parent_agenda(request):
    from accounts.models import User
    if request.user.role != User.Role.PARENT:
        return HttpResponseForbidden("Parents only.")

    parent = getattr(request.user, "parent_profile", None)
    if not parent:
        messages.warning(request, "Parent profile not found.")
        return HttpResponseRedirect(reverse("dashboard"))

    # Select which child to view.
    children = parent.children.select_related("user").all()
    child_id = request.GET.get("child")
    student  = None
    if child_id:
        student = children.filter(pk=child_id).first()
    if not student and children.exists():
        student = children.first()

    if not student:
        return render(request, "agenda/parent_agenda.html", {"children": children, "student": None, "days": []})

    offset = _get_week_offset(request)
    today  = timezone.localdate()
    target = today + datetime.timedelta(weeks=offset)
    monday, sunday = _week_bounds(target)

    from curriculum.models import Enrollment
    enrolled_course_ids = list(
        Enrollment.objects.filter(student=student, status=Enrollment.Status.ACTIVE)
        .values_list("course_id", flat=True)
    )

    items = AgendaItem.objects.filter(
        course_id__in=enrolled_course_ids,
        date__range=(monday, sunday),
    ).select_related("course").order_by("date", "due_time")

    task_map = {}
    if items:
        tasks = StudentTask.objects.filter(student=student, agenda_item__in=items)
        task_map = {t.agenda_item_id: t for t in tasks}

    schedule = ClassSchedule.objects.filter(
        course_id__in=enrolled_course_ids
    ).select_related("course").order_by("day_of_week", "start_time")

    days = []
    for i in range(7):
        day_date = monday + datetime.timedelta(days=i)
        day_items = [it for it in items if it.date == day_date]
        for it in day_items:
            it._task = task_map.get(it.id)
        day_schedule = [s for s in schedule if s.day_of_week == i]
        days.append({
            "date": day_date,
            "is_today": day_date == today,
            "items": day_items,
            "schedule": day_schedule,
        })

    return render(request, "agenda/parent_agenda.html", {
        "children": children,
        "student": student,
        "days": days,
        "monday": monday,
        "sunday": sunday,
        "today": today,
        "offset": offset,
        "prev_offset": offset - 1,
        "next_offset": offset + 1,
    })

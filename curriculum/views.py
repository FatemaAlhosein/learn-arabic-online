"""
curriculum/views.py

Public catalogue + course detail + enrol endpoint + lesson player.

  GET  /courses/                                    -> course_list   (public)
  GET  /courses/<slug>/                             -> course_detail (public)
  POST /courses/<slug>/enrol/                       -> enrol         (student)
  GET  /courses/<slug>/lessons/<lesson_slug>/       -> lesson_detail (gated)

Teacher authoring (login_required + teacher-only):
  GET/POST /courses/teach/new/                      -> course_create
  GET/POST /courses/teach/<slug>/edit/              -> course_edit
  GET      /courses/teach/<slug>/manage/            -> course_manage
  GET/POST /courses/teach/<slug>/lessons/new/       -> lesson_create
  GET/POST /courses/teach/<slug>/lessons/<ls>/edit/ -> lesson_edit
  POST     /courses/teach/<slug>/lessons/<ls>/delete/ -> lesson_delete
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Category, Course, Enrollment, Lesson, Level, LessonProgress,
)
from .services import student_can_enroll


# =========================================================
# Catalogue list — /courses/
# =========================================================
def course_list(request):
    """
    Browseable list of published courses.

    Filters (all optional, all combinable, all driven by querystring):
        ?level=B1
        ?category=grammar
        ?track=kids
        ?q=verbs            (free-text, matches title or description)

    The querystring is also fed back into the template so the filter
    chips show which filters are currently applied.
    """
    qs = (
        Course.objects.filter(is_published=True)
        .select_related("level", "category", "teacher")
        .order_by("-created_at")
    )

    level_code = request.GET.get("level")
    category_slug = request.GET.get("category")
    track = request.GET.get("track")
    q = request.GET.get("q", "").strip()

    if level_code:
        qs = qs.filter(level__code=level_code)
    if category_slug:
        qs = qs.filter(category__slug=category_slug)
    if track:
        qs = qs.filter(track=track)
    if q:
        qs = qs.filter(title__icontains=q) | qs.filter(description__icontains=q)

    context = {
        "courses": qs,
        "levels": Level.objects.all(),
        "categories": Category.objects.filter(is_active=True),
        "tracks": Course.Track.choices,
        # Echo the active filters back so the UI can highlight them.
        "active": {
            "level": level_code or "",
            "category": category_slug or "",
            "track": track or "",
            "q": q,
        },
    }
    return render(request, "curriculum/course_list.html", context)


# =========================================================
# Course detail — /courses/<slug>/
# =========================================================
def course_detail(request, slug):
    """
    Course landing page. Shows description, teacher, lesson outline.

    Eligibility verdict is computed for authenticated *students*; for
    everyone else the page just shows a 'Sign in to enrol' CTA.
    """
    course = get_object_or_404(
        Course.objects.select_related("level", "category", "teacher")
                      .prefetch_related("lessons"),
        slug=slug,
        is_published=True,
    )

    # Default verdict: not signed in / not a student.
    eligibility = None
    is_enrolled = False
    enrollment = None

    if request.user.is_authenticated and request.user.is_student:
        student = getattr(request.user, "student_profile", None)
        if student is not None:
            eligibility = student_can_enroll(student, course)
            enrollment = course.enrollments.filter(student=student).first()
            is_enrolled = enrollment is not None

    # Course final quiz (if any) — exposed as a button when student is enrolled.
    course_final = course.quizzes.filter(
        kind="course_final", is_published=True
    ).first()

    # All published assignments for this course (course-level + lesson-level).
    from assignments.models import Assignment
    course_assignments = Assignment.objects.filter(
        course=course, is_published=True
    ).order_by("due_date", "created_at")
    lesson_assignments_all = Assignment.objects.filter(
        lesson__course=course, is_published=True
    ).select_related("lesson").order_by("lesson__order", "due_date")

    context = {
        "course": course,
        "lessons": course.lessons.all(),  # prefetched above; ordered by Meta.ordering
        "eligibility": eligibility,
        "is_enrolled": is_enrolled,
        "enrollment": enrollment,
        "course_final": course_final,
        "course_assignments": course_assignments,
        "lesson_assignments_all": lesson_assignments_all,
    }
    return render(request, "curriculum/course_detail.html", context)


# =========================================================
# Enrol — POST /courses/<slug>/enrol/
# =========================================================
@login_required
@require_POST
def enrol(request, slug):
    """
    Create an Enrollment row for the current student in this course,
    then redirect to the first lesson.

    Defence in depth: the eligibility check ran in the template too,
    but a malicious POST could bypass that — so we re-run it here.
    """
    course = get_object_or_404(Course, slug=slug, is_published=True)

    # Only students may enrol.
    if not request.user.is_student:
        messages.error(request, "Only student accounts can enrol in courses.")
        return HttpResponseRedirect(
            reverse("curriculum:course_detail", args=[course.slug])
        )

    student = getattr(request.user, "student_profile", None)
    if student is None:
        # Should never happen given role=student auto-creates the profile,
        # but defensive code is cheap.
        messages.error(request, "Your student profile is missing. Contact support.")
        return HttpResponseRedirect(
            reverse("curriculum:course_detail", args=[course.slug])
        )

    # Idempotent: clicking enrol twice is fine.
    enrollment, created = Enrollment.objects.get_or_create(
        student=student,
        course=course,
        defaults={"status": Enrollment.Status.ACTIVE},
    )

    if created:
        # Re-validate eligibility on the server. (We accept the POST and
        # then check; if ineligible, we delete the row we just made.)
        verdict = student_can_enroll(student, course)
        if not verdict.ok:
            enrollment.delete()
            messages.warning(request, verdict.message)
            return HttpResponseRedirect(
                reverse("curriculum:course_detail", args=[course.slug])
            )
        messages.success(request, f"Enrolled in {course.title}.")
        # Fire enrollment notifications (student + teacher)
        try:
            from notifications.services import notify_enrollment
            notify_enrollment(enrollment)
        except Exception:
            pass
    else:
        messages.info(request, "You're already enrolled in this course.")

    # Send the student to the first lesson if there is one, otherwise
    # back to the course detail page.
    first_lesson = course.lessons.order_by("order").first()
    if first_lesson:
        return HttpResponseRedirect(reverse(
            "curriculum:lesson_detail",
            args=[course.slug, first_lesson.slug],
        ))
    return HttpResponseRedirect(
        reverse("curriculum:course_detail", args=[course.slug])
    )


# =========================================================
# Mark a lesson as complete — POST /courses/<slug>/lessons/<lesson_slug>/complete/
# =========================================================
@login_required
@require_POST
def complete_lesson(request, slug, lesson_slug):
    """
    Manual "I've finished this lesson" button. Required for lessons that
    don't have a lesson_quiz to auto-complete them.

    Idempotent: if the lesson is already completed, no DB write happens.

    After marking complete, redirect to the next lesson if there is one;
    otherwise back to the course detail page.
    """
    course = get_object_or_404(Course, slug=slug, is_published=True)
    lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)

    if not request.user.is_student:
        messages.error(request, "Only students can mark lessons complete.")
        return HttpResponseRedirect(
            reverse("curriculum:lesson_detail", args=[slug, lesson_slug])
        )

    student = getattr(request.user, "student_profile", None)
    enrollment = (
        Enrollment.objects
        .filter(student=student, course=course,
                status=Enrollment.Status.ACTIVE)
        .first()
        if student else None
    )
    if enrollment is None:
        messages.warning(request, "Enrol in the course to track progress.")
        return HttpResponseRedirect(
            reverse("curriculum:course_detail", args=[slug])
        )

    progress, _ = LessonProgress.objects.get_or_create(
        enrollment=enrollment,
        lesson=lesson,
        defaults={
            "status": LessonProgress.Status.COMPLETED,
            "completed_at": timezone.now(),
        },
    )
    if progress.status != LessonProgress.Status.COMPLETED:
        progress.status = LessonProgress.Status.COMPLETED
        progress.completed_at = timezone.now()
        progress.save(update_fields=["status", "completed_at"])
        messages.success(request, f"Marked '{lesson.title}' as complete.")

    # Send the student to the next lesson if one exists.
    next_lesson = (
        Lesson.objects
        .filter(course=course, order__gt=lesson.order)
        .order_by("order")
        .first()
    )
    if next_lesson:
        return HttpResponseRedirect(reverse(
            "curriculum:lesson_detail",
            args=[course.slug, next_lesson.slug],
        ))
    return HttpResponseRedirect(
        reverse("curriculum:course_detail", args=[course.slug])
    )


# =========================================================
# Lesson player — /courses/<slug>/lessons/<lesson_slug>/
# =========================================================
def lesson_detail(request, slug, lesson_slug):
    """
    Render a single lesson.

    Access rules:
        is_free_preview = True          -> anyone can view (even anon)
        otherwise                       -> must be authenticated, must be a
                                           student, must have an active
                                           enrolment in this course

    Side effect: when a logged-in enrolled student opens a lesson, we
    upsert a LessonProgress row marked 'in_progress' (unless already
    'completed') and stamp last_viewed_at. This is the only DB write
    on a GET in the whole app — kept tiny and idempotent on purpose.
    """
    # Teachers can preview their own courses even when unpublished.
    # Everyone else only sees published courses.
    _is_teacher_preview = (
        request.user.is_authenticated
        and hasattr(request.user, "role")
        and request.user.role == "teacher"
    )
    if _is_teacher_preview:
        course = get_object_or_404(Course, slug=slug)
    else:
        course = get_object_or_404(Course, slug=slug, is_published=True)

    lesson = get_object_or_404(
        Lesson.objects.prefetch_related("attachments"),
        course=course,
        slug=lesson_slug,
    )

    # Teacher preview: the course's own teacher bypasses all enrollment checks.
    is_teacher_preview = _is_teacher_preview and course.teacher == request.user

    # Decide access.
    enrollment = None
    if not is_teacher_preview and not lesson.is_free_preview:
        if not request.user.is_authenticated or not request.user.is_student:
            messages.warning(request, "Please sign in as a student to view this lesson.")
            return HttpResponseRedirect(
                reverse("login") + f"?next={request.path}"
            )

        student = getattr(request.user, "student_profile", None)
        enrollment = (
            Enrollment.objects.filter(student=student, course=course).first()
            if student else None
        )
        if enrollment is None or enrollment.status != Enrollment.Status.ACTIVE:
            messages.warning(request, "Enrol in the course to view this lesson.")
            return HttpResponseRedirect(
                reverse("curriculum:course_detail", args=[course.slug])
            )

    # Side effect: stamp progress (only when we have an enrolment).
    # Viewing a lesson counts as completing it — this triggers the
    # enrollment-completion check via the post_save signal.
    if enrollment is not None:
        now = timezone.now()
        progress, created = LessonProgress.objects.get_or_create(
            enrollment=enrollment,
            lesson=lesson,
            defaults={
                "status": LessonProgress.Status.COMPLETED,
                "completed_at": now,
                "last_viewed_at": now,
            },
        )
        if not created:
            # Row already existed — only write the status change if needed
            # (avoids firing the completion signal on every re-visit).
            update_fields = ["last_viewed_at"]
            if progress.status != LessonProgress.Status.COMPLETED:
                progress.status = LessonProgress.Status.COMPLETED
                progress.completed_at = now
                update_fields += ["status", "completed_at"]
            progress.last_viewed_at = now
            progress.save(update_fields=update_fields)

    # Build prev / next links so the player has navigation.
    siblings = list(course.lessons.order_by("order"))
    idx = next((i for i, l in enumerate(siblings) if l.pk == lesson.pk), None)
    prev_lesson = siblings[idx - 1] if idx is not None and idx > 0 else None
    next_lesson = siblings[idx + 1] if idx is not None and idx + 1 < len(siblings) else None

    # If we got here via a free-preview lesson, `enrollment` is still None
    # even when the viewer is actually enrolled. Look it up so the
    # completion badge and "Mark as complete" button render correctly.
    if (enrollment is None and request.user.is_authenticated
            and request.user.is_student):
        student = getattr(request.user, "student_profile", None)
        if student is not None:
            enrollment = (
                Enrollment.objects
                .filter(student=student, course=course,
                        status=Enrollment.Status.ACTIVE)
                .first()
            )

    # Pull the existing progress row (if any) for the completion badge.
    progress = None
    completed_lesson_ids = set()
    if enrollment is not None:
        progress = LessonProgress.objects.filter(
            enrollment=enrollment, lesson=lesson,
        ).first()
        completed_lesson_ids = set(
            LessonProgress.objects
            .filter(enrollment=enrollment,
                    status=LessonProgress.Status.COMPLETED)
            .values_list("lesson_id", flat=True)
        )

    # Linked lesson quizzes (Phase 6) — show a "Take quiz" button for each.
    lesson_quizzes = lesson.quizzes.filter(is_published=True)

    # Linked flashcard decks (Phase 9) — show a "Study cards" button for each.
    flashcard_decks = lesson.flashcard_decks.filter(is_published=True)

    # Linked assignments — shown to enrolled students (and teacher preview).
    from assignments.models import Assignment, AssignmentSubmission
    lesson_assignments = lesson.assignments.filter(is_published=True)

    # Pre-fetch this student's submission status for each assignment.
    submission_map = {}
    if enrollment is not None:
        student = getattr(request.user, "student_profile", None)
        if student:
            subs = AssignmentSubmission.objects.filter(
                assignment__in=lesson_assignments, student=student
            ).values("assignment_id", "status")
            submission_map = {s["assignment_id"]: s["status"] for s in subs}

    context = {
        "course": course,
        "lesson": lesson,
        "attachments": lesson.attachments.all(),
        "prev_lesson": prev_lesson,
        "next_lesson": next_lesson,
        "siblings": siblings,
        "progress": progress,
        "lesson_quizzes": lesson_quizzes,
        "flashcard_decks": flashcard_decks,
        "lesson_assignments": lesson_assignments,
        "submission_map": submission_map,
        "completed_lesson_ids": completed_lesson_ids,
        "is_teacher_preview": is_teacher_preview,
    }
    return render(request, "curriculum/lesson_detail.html", context)


# =========================================================
# Public certificate page — /certificates/<code>/
# =========================================================
def certificate(request, code):
    """
    Public, capability-URL-style certificate view.

    Anyone with the 32-char code can view the certificate (so it can be
    shared on LinkedIn etc.), but the code is unguessable. We also
    require the enrolment to be in 'completed' status — protects against
    a leaked code from a partial completion.
    """
    enrollment = get_object_or_404(
        Enrollment.objects
        .select_related("student", "student__user",
                        "course", "course__level", "course__teacher"),
        certificate_code=code,
        status=Enrollment.Status.COMPLETED,
    )
    return render(request, "curriculum/certificate.html", {
        "enrollment": enrollment,
        "course": enrollment.course,
        "student": enrollment.student,
    })


# =========================================================
# Helpers
# =========================================================
def _require_teacher(request, course=None):
    """
    Returns an HttpResponseForbidden if the request user is not a teacher,
    or (when `course` is given) is not the owner of that course.
    Returns None when access is granted.
    """
    from accounts.models import User
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Only teachers can access this page.")
    if course and course.teacher != request.user:
        return HttpResponseForbidden("You can only manage your own courses.")
    return None


# =========================================================
# Teacher — course create
# =========================================================
@login_required
def course_create(request):
    """GET/POST /courses/teach/new/"""
    from .forms import CourseForm
    guard = _require_teacher(request)
    if guard:
        return guard

    form = CourseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        course = form.save(teacher=request.user)
        messages.success(request, f'Course "{course.title}" created.')
        return HttpResponseRedirect(
            reverse("curriculum:course_manage", args=[course.slug])
        )
    return render(request, "curriculum/teach/course_form.html", {
        "form": form,
        "mode": "create",
        "page_title": "Create a new course",
    })


# =========================================================
# Teacher — course edit
# =========================================================
@login_required
def course_edit(request, slug):
    """GET/POST /courses/teach/<slug>/edit/"""
    from .forms import CourseForm
    course = get_object_or_404(Course, slug=slug)
    guard = _require_teacher(request, course)
    if guard:
        return guard

    form = CourseForm(
        request.POST or None,
        request.FILES or None,
        instance=course,
    )
    if request.method == "POST" and form.is_valid():
        form.save(teacher=request.user)
        messages.success(request, "Course updated.")
        return HttpResponseRedirect(
            reverse("curriculum:course_manage", args=[course.slug])
        )
    return render(request, "curriculum/teach/course_form.html", {
        "form": form,
        "course": course,
        "mode": "edit",
        "page_title": f"Edit — {course.title}",
    })


# =========================================================
# Teacher — course manage (lesson list)
# =========================================================
@login_required
def course_manage(request, slug):
    """GET /courses/teach/<slug>/manage/"""
    course = get_object_or_404(
        Course.objects.select_related("level", "category"),
        slug=slug,
    )
    guard = _require_teacher(request, course)
    if guard:
        return guard

    lessons = course.lessons.prefetch_related(
        "quizzes", "flashcard_decks"
    ).order_by("order")

    # Course-level final quiz (if any).
    from assessments.models import Quiz
    course_final_quiz = course.quizzes.filter(
        kind=Quiz.Kind.COURSE_FINAL
    ).first()

    # All assignments for this course (course-level + lesson-level).
    from assignments.models import Assignment
    course_assignments = Assignment.objects.filter(
        course=course
    ).order_by("due_date", "created_at")
    lesson_assignments = Assignment.objects.filter(
        lesson__course=course
    ).select_related("lesson").order_by("lesson__order", "created_at")

    return render(request, "curriculum/teach/course_manage.html", {
        "course": course,
        "lessons": lessons,
        "course_final_quiz": course_final_quiz,
        "course_assignments": course_assignments,
        "lesson_assignments": lesson_assignments,
    })


# =========================================================
# Teacher — lesson create
# =========================================================
@login_required
def lesson_create(request, slug):
    """GET/POST /courses/teach/<slug>/lessons/new/"""
    from .forms import LessonForm
    course = get_object_or_404(Course, slug=slug)
    guard = _require_teacher(request, course)
    if guard:
        return guard

    # Suggest the next order number.
    last_order = course.lessons.order_by("-order").values_list("order", flat=True).first()
    next_order = (last_order or 0) + 1

    initial = {"order": next_order}
    form = LessonForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        lesson = form.save(course=course)
        messages.success(request, f'Lesson "{lesson.title}" added.')
        return HttpResponseRedirect(
            reverse("curriculum:course_manage", args=[course.slug])
        )
    return render(request, "curriculum/teach/lesson_form.html", {
        "form": form,
        "course": course,
        "mode": "create",
        "page_title": f"Add lesson — {course.title}",
    })


# =========================================================
# Teacher — lesson edit
# =========================================================
@login_required
def lesson_edit(request, slug, lesson_slug):
    """GET/POST /courses/teach/<slug>/lessons/<lesson_slug>/edit/"""
    from .forms import LessonForm
    course = get_object_or_404(Course, slug=slug)
    guard = _require_teacher(request, course)
    if guard:
        return guard

    lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)
    form = LessonForm(
        request.POST or None,
        request.FILES or None,
        instance=lesson,
    )
    if request.method == "POST" and form.is_valid():
        form.save(course=course)
        messages.success(request, "Lesson updated.")
        return HttpResponseRedirect(
            reverse("curriculum:course_manage", args=[course.slug])
        )
    return render(request, "curriculum/teach/lesson_form.html", {
        "form": form,
        "course": course,
        "lesson": lesson,
        "mode": "edit",
        "page_title": f"Edit — {lesson.title}",
    })


# =========================================================
# Teacher — lesson delete
# =========================================================
@login_required
@require_POST
def lesson_delete(request, slug, lesson_slug):
    """POST /courses/teach/<slug>/lessons/<lesson_slug>/delete/"""
    course = get_object_or_404(Course, slug=slug)
    guard = _require_teacher(request, course)
    if guard:
        return guard

    lesson = get_object_or_404(Lesson, course=course, slug=lesson_slug)
    title = lesson.title
    lesson.delete()
    messages.success(request, f'Lesson "{title}" deleted.')
    return HttpResponseRedirect(
        reverse("curriculum:course_manage", args=[course.slug])
    )

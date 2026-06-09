"""
dashboards/views.py

A single /dashboard/ entrypoint that dispatches by role:
    student  -> StudentDashboardView   (enrolments + per-course progress)
    teacher  -> TeacherDashboardView   (own courses + recent activity)
    parent   -> ParentDashboardView    (linked children + progress)
    admin    -> AdminDashboardView     (site-wide stats + user management)
    other    -> 403 (defensive — every user should have a role)
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import TemplateView

from accounts.models import User
from assessments.models import Quiz, Submission
from curriculum.models import Course, Enrollment, Lesson, LessonProgress


# =========================================================
# Dispatcher — /dashboard/
# =========================================================
@login_required
def dashboard(request):
    """Single public route. Dispatches to the role-specific view."""
    role = request.user.role

    if role == User.Role.STUDENT:
        return StudentDashboardView.as_view()(request)
    if role == User.Role.TEACHER:
        return TeacherDashboardView.as_view()(request)
    if role == User.Role.PARENT:
        return ParentDashboardView.as_view()(request)
    if role == User.Role.ADMIN:
        return AdminDashboardView.as_view()(request)

    return render(request, "dashboards/no_role.html", status=403)


# =========================================================
# Student dashboard
# =========================================================
class StudentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboards/student.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        student = self.request.user.student_profile

        enrollments = (
            student.enrollments
            .select_related("course", "course__level", "course__category")
            .annotate(total_lessons=Count("course__lessons", distinct=True))
            .order_by("-started_at")
        )

        progress_counts = (
            LessonProgress.objects
            .filter(enrollment__student=student,
                    status=LessonProgress.Status.COMPLETED)
            .values("enrollment_id")
            .annotate(done=Count("id"))
        )
        completed_by_enrollment = {row["enrollment_id"]: row["done"]
                                   for row in progress_counts}

        rows = []
        for e in enrollments:
            done = completed_by_enrollment.get(e.id, 0)
            total = e.total_lessons or 0
            pct = int(round(100 * done / total)) if total else 0
            rows.append({
                "enrollment": e,
                "completed": done,
                "total": total,
                "percent": pct,
            })

        placement_quiz = (
            Quiz.objects
            .filter(kind=Quiz.Kind.PLACEMENT, is_published=True)
            .order_by("-created_at")
            .first()
        )

        ctx.update({
            "student": student,
            "enrollment_rows": rows,
            "active_count": sum(1 for r in rows
                                if r["enrollment"].status == Enrollment.Status.ACTIVE),
            "completed_count": sum(1 for r in rows
                                   if r["enrollment"].status == Enrollment.Status.COMPLETED),
            "placement_quiz": placement_quiz,
        })
        return ctx


# =========================================================
# Teacher dashboard
# =========================================================
class TeacherDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboards/teacher.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        teacher = self.request.user

        courses = (
            Course.objects
            .filter(teacher=teacher)
            .select_related("level", "category")
            .annotate(
                lesson_count=Count("lessons", distinct=True),
                enrollment_count=Count(
                    "enrollments",
                    filter=Q(enrollments__status=Enrollment.Status.ACTIVE),
                    distinct=True,
                ),
            )
            .order_by("-created_at")
        )

        recent = (
            LessonProgress.objects
            .filter(lesson__course__teacher=teacher,
                    last_viewed_at__isnull=False)
            .select_related("lesson", "lesson__course",
                            "enrollment__student__user")
            .order_by("-last_viewed_at")[:10]
        )

        from games.models import GameQuestion, VocabWord
        ctx.update({
            "teacher": teacher,
            "teacher_profile": getattr(teacher, "teacher_profile", None),
            "courses": courses,
            "total_enrollments": sum(c.enrollment_count for c in courses),
            "recent_activity": recent,
            "vocab_count":    VocabWord.objects.filter(is_active=True).count(),
            "sentence_count": GameQuestion.objects.filter(
                game_type=GameQuestion.GameType.SENTENCE_BUILDER, is_active=True).count(),
            "tof_count":      GameQuestion.objects.filter(
                game_type=GameQuestion.GameType.TRUE_OR_FALSE, is_active=True).count(),
        })
        return ctx


# =========================================================
# Parent dashboard
# =========================================================
class ParentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboards/parent.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        parent_profile = self.request.user.parent_profile

        children_qs = (
            parent_profile.children
            .select_related("user", "current_level")
            .annotate(enrollment_count=Count("enrollments"))
            .order_by("user__first_name")
        )

        # For each child build progress rows for their active enrollments.
        enriched_children = []
        for child in children_qs:
            active_enrollments = (
                child.enrollments
                .filter(status=Enrollment.Status.ACTIVE)
                .select_related("course")
                .annotate(total=Count("course__lessons", distinct=True))
            )
            completed_counts = {
                row["enrollment_id"]: row["done"]
                for row in (
                    LessonProgress.objects
                    .filter(enrollment__student=child,
                            status=LessonProgress.Status.COMPLETED)
                    .values("enrollment_id")
                    .annotate(done=Count("id"))
                )
            }
            progress_rows = []
            for e in active_enrollments:
                done = completed_counts.get(e.id, 0)
                total = e.total or 0
                pct = int(round(100 * done / total)) if total else 0
                progress_rows.append({
                    "course_title": e.course.title,
                    "percent": pct,
                    "completed": done,
                    "total": total,
                })
            child.progress_rows = progress_rows
            enriched_children.append(child)

        ctx.update({
            "parent_profile": parent_profile,
            "children": enriched_children,
        })
        return ctx


# =========================================================
# Admin dashboard
# =========================================================
class AdminDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboards/admin.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # User counts by role.
        user_counts = {
            row["role"]: row["count"]
            for row in User.objects.values("role").annotate(count=Count("id"))
        }

        # Pending teacher approvals.
        from accounts.models import TeacherProfile
        pending_teachers = (
            TeacherProfile.objects
            .filter(is_approved=False)
            .select_related("user")
            .order_by("created_at")[:10]
        )

        # Recent signups (last 10).
        recent_users = (
            User.objects
            .order_by("-date_joined")[:10]
        )

        # Course stats.
        course_stats = {
            "total": Course.objects.count(),
            "published": Course.objects.filter(is_published=True).count(),
            "unpublished": Course.objects.filter(is_published=False).count(),
        }

        # Recent enrollments.
        recent_enrollments = (
            Enrollment.objects
            .select_related("student__user", "course")
            .order_by("-started_at")[:10]
        )

        # Enrollment totals.
        enrollment_stats = {
            "active": Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).count(),
            "completed": Enrollment.objects.filter(status=Enrollment.Status.COMPLETED).count(),
        }

        ctx.update({
            "user_counts": user_counts,
            "total_users": User.objects.count(),
            "pending_teachers": pending_teachers,
            "recent_users": recent_users,
            "course_stats": course_stats,
            "enrollment_stats": enrollment_stats,
            "recent_enrollments": recent_enrollments,
        })
        return ctx


# =========================================================
# Student Progress Report
# =========================================================
@login_required
def student_progress(request, student_id=None):
    """
    Full progress report for one student.

    Access rules:
      - student_id=None  → student views their own report
      - student_id given → teacher, parent, or admin only
    """
    viewer = request.user

    # ── Resolve which student we're looking at ──────────────────────────
    if student_id is None:
        # Student viewing their own report
        if viewer.role != User.Role.STUDENT:
            return HttpResponseForbidden("Students only for self-view.")
        student_user = viewer
    else:
        student_user = get_object_or_404(User, pk=student_id, role=User.Role.STUDENT)

        # Permission check
        is_admin   = viewer.role == User.Role.ADMIN or viewer.is_staff
        is_teacher = (
            viewer.role == User.Role.TEACHER
            and Enrollment.objects.filter(
                student__user=student_user,
                course__teacher=viewer,
            ).exists()
        )
        is_parent = (
            viewer.role == User.Role.PARENT
            and hasattr(viewer, "parent_profile")
            and viewer.parent_profile.children.filter(user=student_user).exists()
        )
        if not (is_admin or is_teacher or is_parent):
            return HttpResponseForbidden("You don't have access to this student's report.")

    student_profile = get_object_or_404(
        __import__("accounts.models", fromlist=["StudentProfile"]).StudentProfile,
        user=student_user,
    )

    # ── Enrollments + per-course data ──────────────────────────────────
    enrollments = (
        Enrollment.objects
        .filter(student=student_profile)
        .select_related("course", "course__level", "course__category", "course__teacher")
        .order_by("-started_at")
    )

    # Total lessons per course (one query)
    lesson_counts = {
        row["course_id"]: row["total"]
        for row in Lesson.objects.values("course_id").annotate(total=Count("id"))
    }

    # Completed lessons per enrollment (one query)
    completed_counts = {
        row["enrollment_id"]: row["done"]
        for row in LessonProgress.objects
        .filter(enrollment__student=student_profile,
                status=LessonProgress.Status.COMPLETED)
        .values("enrollment_id")
        .annotate(done=Count("id"))
    }

    # ── Assignments ────────────────────────────────────────────────────
    from assignments.models import AssignmentSubmission
    submissions = (
        AssignmentSubmission.objects
        .filter(student=student_profile)
        .select_related("assignment", "assignment__course", "assignment__lesson")
        .order_by("-submitted_at")
    )
    graded_submissions = [s for s in submissions if s.score is not None]
    avg_score = (
        round(sum(s.score_percent for s in graded_submissions) / len(graded_submissions))
        if graded_submissions else None
    )

    # ── Quiz attempts ──────────────────────────────────────────────────
    quiz_attempts = (
        Submission.objects
        .filter(student=student_profile, status="completed")
        .select_related("quiz", "quiz__course", "quiz__lesson")
        .order_by("-started_at")[:20]
    )

    # ── Recent lesson activity ─────────────────────────────────────────
    recent_activity = (
        LessonProgress.objects
        .filter(enrollment__student=student_profile, last_viewed_at__isnull=False)
        .select_related("lesson", "lesson__course", "enrollment")
        .order_by("-last_viewed_at")[:8]
    )

    # ── Build course rows ──────────────────────────────────────────────
    course_rows = []
    for e in enrollments:
        total = lesson_counts.get(e.course_id, 0)
        done  = completed_counts.get(e.id, 0)
        pct   = int(round(100 * done / total)) if total else 0

        # Assignments for this course
        course_subs = [
            s for s in submissions
            if s.assignment.course_id == e.course_id
        ]

        course_rows.append({
            "enrollment": e,
            "total":      total,
            "done":       done,
            "percent":    pct,
            "submissions": course_subs,
        })

    # ── Summary stats ──────────────────────────────────────────────────
    total_lessons_done = sum(r["done"] for r in course_rows)
    total_lessons_all  = sum(r["total"] for r in course_rows)
    quizzes_passed     = sum(1 for a in quiz_attempts if a.passed)

    return render(request, "dashboards/student_progress.html", {
        "student_user":       student_user,
        "student_profile":    student_profile,
        "course_rows":        course_rows,
        "submissions":        submissions,
        "graded_submissions": graded_submissions,
        "avg_score":          avg_score,
        "quiz_attempts":      quiz_attempts,
        "quizzes_passed":     quizzes_passed,
        "recent_activity":    recent_activity,
        "total_lessons_done": total_lessons_done,
        "total_lessons_all":  total_lessons_all,
        "viewer_role":        viewer.role,
    })

"""
assignments/views.py

Teacher views:
  assignment_create, assignment_edit, assignment_delete
  submission_list  — all submissions for one assignment
  grade_submission — grade one student's submission

Student views:
  assignment_detail — view + submit
  my_submission     — view own grade + feedback
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Assignment, AssignmentSubmission


# =========================================================
# Helpers
# =========================================================
def _require_teacher_assignment(request, assignment):
    """Return error response if user isn't the assignment's teacher, else None."""
    from accounts.models import User
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")
    if assignment.created_by != request.user:
        return HttpResponseForbidden("You can only manage your own assignments.")
    return None


def _get_student_or_403(request):
    if not request.user.is_student:
        raise Http404("Only students can submit assignments.")
    student = getattr(request.user, "student_profile", None)
    if student is None:
        raise Http404("Student profile missing.")
    return student


# =========================================================
# Teacher — assignment create / edit / delete
# =========================================================
@login_required
def assignment_create(request):
    from accounts.models import User
    from .forms import AssignmentForm

    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    # Pre-fill lesson or course from query string.
    lesson, course = None, None
    if lesson_id := request.GET.get("lesson"):
        from curriculum.models import Lesson
        try:
            lesson = Lesson.objects.get(pk=lesson_id, course__teacher=request.user)
        except Lesson.DoesNotExist:
            pass
    elif course_id := request.GET.get("course"):
        from curriculum.models import Course
        try:
            course = Course.objects.get(pk=course_id, teacher=request.user)
        except Course.DoesNotExist:
            pass

    if request.method == "POST":
        form = AssignmentForm(request.POST, teacher=request.user)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.created_by = request.user
            assignment.save()
            messages.success(request, f'Assignment "{assignment.title}" created.')
            # Redirect back to the course manage page.
            course_slug = assignment.scope_course.slug
            return HttpResponseRedirect(
                reverse("curriculum:course_manage", args=[course_slug])
            )
    else:
        form = AssignmentForm(
            teacher=request.user, lesson=lesson, course=course
        )

    return render(request, "assignments/teach/assignment_form.html", {
        "form": form,
        "mode": "create",
        "page_title": "New assignment",
    })


@login_required
def assignment_edit(request, assignment_id):
    from .forms import AssignmentForm
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    err = _require_teacher_assignment(request, assignment)
    if err:
        return err

    if request.method == "POST":
        form = AssignmentForm(request.POST, instance=assignment, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Assignment updated.")
            return HttpResponseRedirect(
                reverse("assignments:submission_list", args=[assignment.id])
            )
    else:
        form = AssignmentForm(instance=assignment, teacher=request.user)

    return render(request, "assignments/teach/assignment_form.html", {
        "form": form,
        "assignment": assignment,
        "mode": "edit",
        "page_title": f"Edit — {assignment.title}",
    })


@login_required
@require_POST
def assignment_delete(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    err = _require_teacher_assignment(request, assignment)
    if err:
        return err

    course_slug = assignment.scope_course.slug
    title = assignment.title
    assignment.delete()
    messages.success(request, f'Assignment "{title}" deleted.')
    return HttpResponseRedirect(
        reverse("curriculum:course_manage", args=[course_slug])
    )


# =========================================================
# Teacher — see all submissions for an assignment
# =========================================================
@login_required
def submission_list(request, assignment_id):
    assignment = get_object_or_404(
        Assignment.objects.prefetch_related(
            "submissions__student__user"
        ),
        pk=assignment_id,
    )
    err = _require_teacher_assignment(request, assignment)
    if err:
        return err

    submissions = assignment.submissions.select_related(
        "student__user", "graded_by"
    ).order_by("-submitted_at")

    pending_count = submissions.filter(
        status=AssignmentSubmission.Status.SUBMITTED
    ).count()

    return render(request, "assignments/teach/submission_list.html", {
        "assignment": assignment,
        "submissions": submissions,
        "pending_count": pending_count,
    })


# =========================================================
# Teacher — grade one submission
# =========================================================
@login_required
def grade_submission(request, assignment_id, submission_id):
    from .forms import GradeForm
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    err = _require_teacher_assignment(request, assignment)
    if err:
        return err

    submission = get_object_or_404(
        AssignmentSubmission.objects.select_related("student__user"),
        pk=submission_id,
        assignment=assignment,
    )

    if request.method == "POST":
        form = GradeForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.status = AssignmentSubmission.Status.GRADED
            sub.graded_at = timezone.now()
            sub.graded_by = request.user
            sub.save()
            messages.success(
                request,
                f"Grade saved for {submission.student.user.first_name or submission.student.user.email}."
            )
            # Notify student their work has been graded
            try:
                from notifications.services import notify_assignment_graded
                notify_assignment_graded(sub)
            except Exception:
                pass
            return HttpResponseRedirect(
                reverse("assignments:submission_list", args=[assignment.id])
            )
    else:
        form = GradeForm(instance=submission)

    return render(request, "assignments/teach/grade_form.html", {
        "form": form,
        "assignment": assignment,
        "submission": submission,
    })


# =========================================================
# Student — view assignment + submit
# =========================================================
@login_required
def assignment_detail(request, assignment_id):
    from .forms import SubmissionForm
    assignment = get_object_or_404(
        Assignment, pk=assignment_id, is_published=True
    )
    student = _get_student_or_403(request)

    # Check student is enrolled in the parent course.
    from curriculum.models import Enrollment
    course = assignment.scope_course
    enrollment = Enrollment.objects.filter(
        student=student, course=course,
        status=Enrollment.Status.ACTIVE,
    ).first()
    if enrollment is None:
        messages.warning(request, "Enrol in the course to access this assignment.")
        return HttpResponseRedirect(
            reverse("curriculum:course_detail", args=[course.slug])
        )

    # Get or initialise the submission row.
    submission, _ = AssignmentSubmission.objects.get_or_create(
        assignment=assignment,
        student=student,
    )

    if request.method == "POST":
        if submission.status == AssignmentSubmission.Status.GRADED:
            messages.info(request, "This assignment has already been graded and cannot be re-submitted.")
            return HttpResponseRedirect(
                reverse("assignments:assignment_detail", args=[assignment.id])
            )
        form = SubmissionForm(request.POST, request.FILES, instance=submission)
        # Only include fields the assignment allows.
        if not assignment.allow_text_response:
            form.fields.pop("text_response", None)
        if not assignment.allow_file_upload:
            form.fields.pop("file", None)

        if form.is_valid():
            sub = form.save(commit=False)
            sub.status = AssignmentSubmission.Status.SUBMITTED
            sub.submitted_at = timezone.now()
            sub.save()
            messages.success(request, "Assignment submitted successfully!")
            # Notify teacher
            try:
                from notifications.services import notify_assignment_submitted
                notify_assignment_submitted(sub)
            except Exception:
                pass
            return HttpResponseRedirect(
                reverse("assignments:assignment_detail", args=[assignment.id])
            )
    else:
        form = SubmissionForm(instance=submission)
        if not assignment.allow_text_response:
            form.fields.pop("text_response", None)
        if not assignment.allow_file_upload:
            form.fields.pop("file", None)

    return render(request, "assignments/assignment_detail.html", {
        "assignment": assignment,
        "submission": submission,
        "form": form,
        "course": course,
    })

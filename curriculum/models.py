"""
curriculum/models.py

Phase 4A: Level + Category (the lookup tables)
Phase 4B: Course + Lesson + LessonAttachment (the content)
Phase 4C: Enrollment + LessonProgress (the student's relationship to courses)
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


# =========================================================
# Level — A1 → C2; the prerequisite chain
# =========================================================
class Level(models.Model):
    """
    CEFR-style proficiency level (A1, A2, B1, B2, C1, C2).

    `order` is the gating field. A student with `current_level.order = 2`
    can only enrol in courses whose `level.order` <= 3 (next-level rule),
    or in courses with no level (open courses).

    Levels are seeded once by an admin (or via fixture) and almost never
    change — the table is small and immutable in practice.
    """

    code = models.CharField(
        max_length=4,
        unique=True,
        help_text="e.g. A1, A2, B1, B2, C1, C2",
    )
    name = models.CharField(
        max_length=80,
        help_text="Human-readable name, e.g. 'Beginner 1'",
    )
    order = models.PositiveSmallIntegerField(
        unique=True,
        help_text="Sorting + prerequisite check. A1=1, A2=2, ..., C2=6.",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "level"
        verbose_name_plural = "levels"

    def __str__(self):
        return f"{self.code} — {self.name}"


# =========================================================
# Category — Grammar, Reading, Listening, ...
# =========================================================
class Category(models.Model):
    """
    Course grouping. A course belongs to exactly one category.

    Used for navigation and filtering in the public catalogue.
    """

    slug = models.SlugField(
        max_length=80,
        unique=True,
        help_text="URL-safe identifier, e.g. 'grammar', 'listening'.",
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40,
        blank=True,
        help_text="Optional Bootstrap Icon name, e.g. 'book', 'mic-fill'.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Hide a category from the public catalogue without deleting it.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "category"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-fill slug if the admin left it blank.
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# =========================================================
# Course — the unit of enrolment
# =========================================================
class Course(models.Model):
    """
    A course is the unit a student enrols in.

    Eligibility rule (enforced in code, not at the DB):
      - if level is NULL  -> open course, anyone can enrol.
      - else              -> student.current_level.order >= level.order - 1.
      - track filter      -> 'all' visible to everyone; otherwise must match
                             student.age_track.
    """

    class Track(models.TextChoices):
        ALL   = "all",   "All ages"
        KIDS  = "kids",  "Kids (under 12)"
        TEEN  = "teen",  "Teens (12–17)"
        ADULT = "adult", "Adults (18+)"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)

    # Level FK is nullable -> open course (no prerequisite).
    level = models.ForeignKey(
        Level,
        on_delete=models.PROTECT,
        related_name="courses",
        null=True,
        blank=True,
        help_text="Leave empty for an open course (no level prerequisite).",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    track = models.CharField(
        max_length=8,
        choices=Track.choices,
        default=Track.ALL,
    )

    # Teacher = User with role=teacher.  limit_choices_to filters the admin
    # dropdown; it isn't a DB-level constraint, so we still validate in clean().
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses_taught",
        limit_choices_to={"role": "teacher"},
    )

    thumbnail = models.ImageField(
        upload_to="course_thumbnails/",
        null=True,
        blank=True,
    )
    is_published = models.BooleanField(
        default=False,
        help_text="Unpublished courses are hidden from the catalogue.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "course"
        verbose_name_plural = "courses"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def clean(self):
        # Enforce that the chosen teacher actually has role=teacher,
        # because limit_choices_to is only enforced in admin forms.
        # Use teacher_id to avoid RelatedObjectDoesNotExist when teacher
        # hasn't been assigned yet (e.g. teacher-facing form sets it after
        # form.is_valid() runs full_clean on the unsaved instance).
        if self.teacher_id and self.teacher.role != "teacher":
            raise ValidationError({"teacher": "Selected user is not a teacher."})


# =========================================================
# Lesson — the unit a student watches / reads
# =========================================================
class Lesson(models.Model):
    """
    A lesson belongs to exactly one course. Lessons are ordered within a
    course (1, 2, 3, ...). The first lesson is often `is_free_preview=True`
    so visitors can sample the course before enrolling.

    Content sources (any combination):
      - body_markdown        -> text content rendered by the lesson player
      - primary_video_url    -> the "main" video, e.g. a YouTube/Vimeo embed
      - LessonAttachment     -> audio clips, PDFs, slide decks, images, ...
    """

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    order = models.PositiveSmallIntegerField(
        help_text="Display order within the course; 1 is first.",
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    body_markdown = models.TextField(
        blank=True,
        help_text="Lesson body in markdown. Rendered by the lesson player.",
    )
    primary_video_url = models.URLField(
        blank=True,
        help_text="External video embed URL (YouTube /embed/<id> or "
                  "player.vimeo.com/video/<id>). Used only when no "
                  "video_file is uploaded.",
    )
    video_file = models.FileField(
        upload_to="lesson_videos/",
        blank=True,
        null=True,
        help_text="Self-hosted MP4 / WebM. Takes precedence over "
                  "primary_video_url when set.",
    )
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    is_free_preview = models.BooleanField(
        default=False,
        help_text="Free previews are viewable without enrolment.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["course", "order"]
        constraints = [
            # A course can't have two lessons at the same order.
            models.UniqueConstraint(
                fields=["course", "order"],
                name="lesson_unique_order_per_course",
            ),
            # Slugs unique within a course (not globally; a 'introduction'
            # slug is fine in many courses).
            models.UniqueConstraint(
                fields=["course", "slug"],
                name="lesson_unique_slug_per_course",
            ),
        ]
        verbose_name = "lesson"
        verbose_name_plural = "lessons"

    def __str__(self):
        return f"{self.course.title} · {self.order}. {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


# =========================================================
# LessonAttachment — audio / pdf / docx / pptx / image / ...
# =========================================================
class LessonAttachment(models.Model):
    """
    One file or external URL attached to a lesson.

    Constraint (enforced in clean()):
      Exactly ONE of `file` and `external_url` must be set — never both,
      never neither.
    """

    class Kind(models.TextChoices):
        AUDIO = "audio", "Audio"
        PDF   = "pdf",   "PDF"
        DOCX  = "docx",  "Word document"
        PPTX  = "pptx",  "Slide deck"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        OTHER = "other", "Other"

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    kind = models.CharField(max_length=8, choices=Kind.choices)
    title = models.CharField(max_length=200)

    file = models.FileField(
        upload_to="lesson_attachments/",
        blank=True,
        null=True,
    )
    external_url = models.URLField(blank=True)

    order = models.PositiveSmallIntegerField(default=0)
    is_downloadable = models.BooleanField(
        default=True,
        help_text="If False, students can view but not download.",
    )
    size_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Auto-filled on save when an uploaded file is present.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["lesson", "order"]
        verbose_name = "lesson attachment"
        verbose_name_plural = "lesson attachments"

    def __str__(self):
        return f"{self.get_kind_display()} · {self.title}"

    def clean(self):
        has_file = bool(self.file)
        has_url = bool(self.external_url)
        if has_file and has_url:
            raise ValidationError(
                "Provide either an uploaded file OR an external URL, not both."
            )
        if not has_file and not has_url:
            raise ValidationError(
                "Provide an uploaded file or an external URL."
            )

    def save(self, *args, **kwargs):
        # Auto-fill size_bytes when a real file is attached.
        if self.file and hasattr(self.file, "size"):
            self.size_bytes = self.file.size
        else:
            self.size_bytes = None
        super().save(*args, **kwargs)


# =========================================================
# Enrollment — the student's relationship to a course
# =========================================================
class Enrollment(models.Model):
    """
    A student enrols in a course. One row per (student, course) pair.

    Status lifecycle:
        active     -> currently studying
        completed  -> all required lessons done, certificate may be issued
        cancelled  -> student withdrew or admin revoked access

    The eligibility rule (level prereq + age track) is checked BEFORE creating
    an Enrollment row — typically in a service helper `student_can_enroll()`
    in Phase 4E. The model itself doesn't re-check, because by the time a row
    exists, eligibility has already been validated.
    """

    class Status(models.TextChoices):
        ACTIVE    = "active",    "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey(
        "accounts.StudentProfile",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="enrollments",
        help_text="PROTECT — never delete a course that has enrolments.",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_url = models.URLField(
        blank=True,
        help_text="Optional override (e.g. PDF on S3). Usually empty; "
                  "the on-site cert page is reachable via certificate_code.",
    )
    certificate_code = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text="Stable token used as the URL slug for the public "
                  "certificate page. Auto-set when the course is completed.",
    )

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            # A student can enrol in a course only once.
            models.UniqueConstraint(
                fields=["student", "course"],
                name="enrollment_unique_student_course",
            ),
        ]
        verbose_name = "enrollment"
        verbose_name_plural = "enrollments"

    def __str__(self):
        return f"{self.student} → {self.course} ({self.status})"

    def get_certificate_path(self):
        """Return the on-site certificate URL path, or '' if not yet earned."""
        if not self.certificate_code:
            return ""
        from django.urls import reverse
        return reverse("certificate", args=[self.certificate_code])


# =========================================================
# LessonProgress — per-lesson completion within an enrolment
# =========================================================
class LessonProgress(models.Model):
    """
    Tracks one student's progress through one lesson of one course.

    Hangs off Enrollment (not directly off StudentProfile) because the same
    student could in theory re-enrol in a course later — each enrolment has
    its own progress trail.

    Status lifecycle:
        not_started  -> default; row may not even exist yet
        in_progress  -> student opened the lesson but didn't finish
        completed    -> reached the end / passed the lesson quiz
    """

    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED   = "completed",   "Completed"

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_entries",
    )
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )
    last_viewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["enrollment", "lesson__order"]
        constraints = [
            # One progress row per (enrolment, lesson).
            models.UniqueConstraint(
                fields=["enrollment", "lesson"],
                name="lessonprogress_unique_enrollment_lesson",
            ),
        ]
        verbose_name = "lesson progress"
        verbose_name_plural = "lesson progress"

    def __str__(self):
        return f"{self.enrollment.student} · {self.lesson.title} ({self.status})"

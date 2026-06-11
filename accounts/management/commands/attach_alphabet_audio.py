"""
Management command: attach_alphabet_audio

Uploads Arabic alphabet MP3 files from Arabic-audio/ to Cloudinary,
then creates LessonAttachment records linked to the correct lessons
in ALL courses whose slug contains "alphabet".

Usage:
    python manage.py attach_alphabet_audio
    python manage.py attach_alphabet_audio --dry-run

Safe to re-run — skips attachments that already exist (matched by title).
Requires CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
to be set as environment variables.
"""

import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


# ── Audio → lesson mapping (keyed by lesson ORDER, not slug) ─────────────────
#
# Each entry: (lesson_order, filename_stem, display_title, attachment_order)
#
# Lesson order:
#   1 → intro / full alphabet overview
#   2 → first group  (ا – ذ: alif → thaal, letters 1–9)
#   3 → second group (ر – ض: ra → daad,  letters 10–15)
#   4 → third group  (ط – ي: taa → ya,   letters 16–28)

LESSON_AUDIO = [
    # ── Lesson 1 — Intro ──────────────────────────────────────────────────────
    (1, "full-arabic-alphabet", "🔊 Full Alphabet Audio", 1),

    # ── Lesson 2 — ا to ذ ────────────────────────────────────────────────────
    (2, "alif-letter-name",  "ا Alef — letter name",    1),
    (2, "alif-letter-sound", "ا Alef — pronunciation",  2),
    (2, "ba-letter-name",    "ب Ba — letter name",      3),
    (2, "ba-letter-sound",   "ب Ba — pronunciation",    4),
    (2, "ta-letter-name",    "ت Ta — letter name",      5),
    (2, "ta-letter-sound",   "ت Ta — pronunciation",    6),
    (2, "tha-letter-name",   "ث Tha — letter name",     7),
    (2, "tha-letter-sound",  "ث Tha — pronunciation",   8),
    (2, "jiim-letter-name",  "ج Jim — letter name",     9),
    (2, "jiim-letter-sound", "ج Jim — pronunciation",   10),
    (2, "hha-letter-name",   "ح Ha — letter name",      11),
    (2, "hha-letter-sound",  "ح Ha — pronunciation",    12),
    (2, "kha-letter-name",   "خ Kha — letter name",     13),
    (2, "kha-letter-sound",  "خ Kha — pronunciation",   14),
    (2, "daal-letter-name",  "د Dal — letter name",     15),
    (2, "daal-letter-sound", "د Dal — pronunciation",   16),
    (2, "thaal-letter-name", "ذ Dhal — letter name",    17),
    (2, "thaal-letter-sound","ذ Dhal — pronunciation",  18),

    # ── Lesson 3 — ر to ض ────────────────────────────────────────────────────
    (3, "ra-letter-name",    "ر Ra — letter name",      1),
    (3, "ra-letter-sound",   "ر Ra — pronunciation",    2),
    (3, "zay-letter-name",   "ز Zay — letter name",     3),
    (3, "zay-letter-sound",  "ز Zay — pronunciation",   4),
    (3, "siin-letter-name",  "س Sin — letter name",     5),
    (3, "siin-letter-sound", "س Sin — pronunciation",   6),
    (3, "shiin-letter-name", "ش Shin — letter name",    7),
    (3, "shiin-letter-sound","ش Shin — pronunciation",  8),
    (3, "saad-letter-name",  "ص Sad — letter name",     9),
    (3, "saad-letter-sound", "ص Sad — pronunciation",   10),
    (3, "daad-letter-name",  "ض Dad — letter name",     11),
    (3, "daad-letter-sound", "ض Dad — pronunciation",   12),

    # ── Lesson 4 — ط to ي ────────────────────────────────────────────────────
    (4, "taa-letter-name",   "ط Tah — letter name",     1),
    (4, "taa-letter-sound",  "ط Tah — pronunciation",   2),
    (4, "thaa-letter-name",  "ظ Zah — letter name",     3),
    (4, "thaa-letter-sound", "ظ Zah — pronunciation",   4),
    (4, "ayn-letter-name",   "ع Ayn — letter name",     5),
    (4, "ayn-letter-sound",  "ع Ayn — pronunciation",   6),
    (4, "ghayn-letter-name", "غ Ghayn — letter name",   7),
    (4, "ghayn-letter-sound","غ Ghayn — pronunciation", 8),
    (4, "fa-letter-name",    "ف Fa — letter name",      9),
    (4, "fa-letter-sound",   "ف Fa — pronunciation",    10),
    (4, "qaf-letter-name",   "ق Qaf — letter name",     11),
    (4, "qaf-letter-sound",  "ق Qaf — pronunciation",   12),
    (4, "kaf-letter-name",   "ك Kaf — letter name",     13),
    (4, "kaf-letter-sound",  "ك Kaf — pronunciation",   14),
    (4, "lam-letter-name",   "ل Lam — letter name",     15),
    (4, "lam-letter-sound",  "ل Lam — pronunciation",   16),
    (4, "miim-letter-name",  "م Mim — letter name",     17),
    (4, "miim-letter-sound", "م Mim — pronunciation",   18),
    (4, "nuun-letter-name",  "ن Nun — letter name",     19),
    (4, "nuun-letter-sound", "ن Nun — pronunciation",   20),
    (4, "ha-letter-name",    "ه Ha — letter name",      21),
    (4, "ha-letter-sound",   "ه Ha — pronunciation",    22),
    (4, "waw-letter-name",   "و Waw — letter name",     23),
    (4, "waw-letter-sound",  "و Waw — pronunciation",   24),
    (4, "ya-letter-name",    "ي Ya — letter name",      25),
    (4, "ya-letter-sound",   "ي Ya — pronunciation",    26),
]

# Folder relative to project root: Arabic-audio/
AUDIO_DIR = Path(__file__).resolve().parents[3] / "Arabic-audio"


class Command(BaseCommand):
    help = (
        "Upload Arabic alphabet audio to Cloudinary and attach to all courses "
        "whose slug contains 'alphabet'."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be done without uploading or saving.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # ── imports ────────────────────────────────────────────────────────────
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError:
            raise CommandError("cloudinary not installed. Run: pip install cloudinary")

        from curriculum.models import Course, Lesson, LessonAttachment

        # ── Cloudinary config ──────────────────────────────────────────────────
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
        api_key    = os.environ.get("CLOUDINARY_API_KEY", "")
        api_secret = os.environ.get("CLOUDINARY_API_SECRET", "")

        if not all([cloud_name, api_key, api_secret]):
            raise CommandError(
                "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET."
            )

        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)

        # ── find all alphabet courses ──────────────────────────────────────────
        courses = Course.objects.filter(slug__icontains="alphabet")
        if not courses.exists():
            raise CommandError(
                "No courses found with 'alphabet' in the slug. "
                "Run `python manage.py seed_demo_content` first."
            )

        self.stdout.write(f"Found {courses.count()} alphabet course(s):")
        for c in courses:
            self.stdout.write(f"  • {c.title} ({c.slug})")
        self.stdout.write(f"Audio folder: {AUDIO_DIR}\n")

        if not AUDIO_DIR.exists():
            raise CommandError(f"Audio folder not found: {AUDIO_DIR}")

        # ── cache Cloudinary URLs (upload once, reuse across courses) ──────────
        cloudinary_cache = {}   # file_stem → secure_url

        total_created = 0
        total_skipped = 0
        total_missing = 0

        for course in courses:
            self.stdout.write(self.style.HTTP_INFO(f"\n── {course.title} ──"))

            # Build a lookup: order → lesson
            lesson_by_order = {
                l.order: l
                for l in Lesson.objects.filter(course=course)
            }

            created = skipped = missing = 0

            for lesson_order, file_stem, title, attach_order in LESSON_AUDIO:
                lesson = lesson_by_order.get(lesson_order)
                if not lesson:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠ No lesson at order {lesson_order} — skipping '{title}'"
                        )
                    )
                    skipped += 1
                    continue

                # Skip if already attached
                if LessonAttachment.objects.filter(lesson=lesson, title=title).exists():
                    self.stdout.write(f"  ✓ Already exists: [{lesson_order}] {title}")
                    skipped += 1
                    continue

                # Find MP3
                mp3_path = AUDIO_DIR / f"{file_stem}.mp3"
                if not mp3_path.exists():
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ File not found: {mp3_path.name}")
                    )
                    missing += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"  [dry-run] Would attach: {mp3_path.name} → lesson {lesson_order}"
                    )
                    continue

                # Upload to Cloudinary (or reuse cached URL)
                if file_stem not in cloudinary_cache:
                    self.stdout.write(f"  ↑ Uploading {mp3_path.name} …", ending="")
                    try:
                        result = cloudinary.uploader.upload(
                            str(mp3_path),
                            resource_type="video",
                            folder="learn_arabic/audio/alphabet",
                            public_id=file_stem,
                            overwrite=False,
                        )
                        cloudinary_cache[file_stem] = result["secure_url"]
                        self.stdout.write(" uploaded")
                    except Exception as exc:
                        self.stdout.write(self.style.ERROR(f" FAILED: {exc}"))
                        continue
                else:
                    self.stdout.write(f"  ↑ {mp3_path.name} (reusing cached URL)")

                url = cloudinary_cache[file_stem]

                # Create the DB record
                attachment = LessonAttachment(
                    lesson=lesson,
                    kind=LessonAttachment.Kind.AUDIO,
                    title=title,
                    external_url=url,
                    order=attach_order,
                    is_downloadable=True,
                )
                attachment.full_clean()
                attachment.save()
                self.stdout.write(self.style.SUCCESS(f"    ✓ saved → {lesson.title}"))
                created += 1

            self.stdout.write(
                f"  Created: {created} | Skipped: {skipped} | Missing: {missing}"
            )
            total_created += created
            total_skipped += skipped
            total_missing += missing

        # ── summary ────────────────────────────────────────────────────────────
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — nothing was saved."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All done. Total created: {total_created} | "
                    f"Skipped: {total_skipped} | Missing files: {total_missing}"
                )
            )

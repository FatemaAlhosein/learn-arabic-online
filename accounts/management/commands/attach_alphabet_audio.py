"""
Management command: attach_alphabet_audio

Uploads Arabic alphabet MP3 files from Arabic-audio/ to Cloudinary,
then creates LessonAttachment records linked to the correct lessons
in the "Arabic Alphabet Mastery" course.

Usage:
    python manage.py attach_alphabet_audio

Safe to re-run — skips attachments that already exist (matched by title).
Requires CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
to be set as environment variables.
"""

import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


# ── Audio → lesson mapping ────────────────────────────────────────────────────
#
# Each entry: (lesson_slug, filename_stem, display_title, order)
#
# Lesson slugs come from seed_demo_content:
#   welcome-to-arabic           → Lesson 1 (intro + full alphabet)
#   letters-alef-to-thal        → Lesson 2 (ا – خ: alif, ba, ta, tha, jiim, hha, kha)
#   letters-ra-to-dad           → Lesson 3 (ر – ض: ra, zay, siin, shiin, saad, daad)
#   letters-ta-to-ya            → Lesson 4 (ط – ي: taa, thaa, ayn, ghayn, fa, qaf, kaf,
#                                            lam, miim, nuun, ha, waw, ya)
#   alphabet-practice-quiz      → Lesson 5 (quiz — no audio)

LESSON_AUDIO = [
    # ── Lesson 1 ─────────────────────────────────────────────────────────────
    ("welcome-to-arabic", "full-arabic-alphabet", "🔊 Full Alphabet Audio", 1),

    # ── Lesson 2 (ا – خ) ──────────────────────────────────────────────────
    ("letters-alef-to-thal", "alif-letter-name",  "ا Alef — letter name",  1),
    ("letters-alef-to-thal", "alif-letter-sound", "ا Alef — pronunciation", 2),
    ("letters-alef-to-thal", "ba-letter-name",    "ب Ba — letter name",     3),
    ("letters-alef-to-thal", "ba-letter-sound",   "ب Ba — pronunciation",   4),
    ("letters-alef-to-thal", "ta-letter-name",    "ت Ta — letter name",     5),
    ("letters-alef-to-thal", "ta-letter-sound",   "ت Ta — pronunciation",   6),
    ("letters-alef-to-thal", "tha-letter-name",   "ث Tha — letter name",    7),
    ("letters-alef-to-thal", "tha-letter-sound",  "ث Tha — pronunciation",  8),
    ("letters-alef-to-thal", "jiim-letter-name",  "ج Jim — letter name",    9),
    ("letters-alef-to-thal", "jiim-letter-sound", "ج Jim — pronunciation",  10),
    ("letters-alef-to-thal", "hha-letter-name",   "ح Ha — letter name",     11),
    ("letters-alef-to-thal", "hha-letter-sound",  "ح Ha — pronunciation",   12),
    ("letters-alef-to-thal", "kha-letter-name",   "خ Kha — letter name",    13),
    ("letters-alef-to-thal", "kha-letter-sound",  "خ Kha — pronunciation",  14),
    ("letters-alef-to-thal", "daal-letter-name",  "د Dal — letter name",    15),
    ("letters-alef-to-thal", "daal-letter-sound", "د Dal — pronunciation",  16),
    ("letters-alef-to-thal", "thaal-letter-name", "ذ Dhal — letter name",   17),
    ("letters-alef-to-thal", "thaal-letter-sound","ذ Dhal — pronunciation", 18),

    # ── Lesson 3 (ر – ض) ──────────────────────────────────────────────────
    ("letters-ra-to-dad", "ra-letter-name",    "ر Ra — letter name",     1),
    ("letters-ra-to-dad", "ra-letter-sound",   "ر Ra — pronunciation",   2),
    ("letters-ra-to-dad", "zay-letter-name",   "ز Zay — letter name",    3),
    ("letters-ra-to-dad", "zay-letter-sound",  "ز Zay — pronunciation",  4),
    ("letters-ra-to-dad", "siin-letter-name",  "س Sin — letter name",    5),
    ("letters-ra-to-dad", "siin-letter-sound", "س Sin — pronunciation",  6),
    ("letters-ra-to-dad", "shiin-letter-name", "ش Shin — letter name",   7),
    ("letters-ra-to-dad", "shiin-letter-sound","ش Shin — pronunciation", 8),
    ("letters-ra-to-dad", "saad-letter-name",  "ص Sad — letter name",    9),
    ("letters-ra-to-dad", "saad-letter-sound", "ص Sad — pronunciation",  10),
    ("letters-ra-to-dad", "daad-letter-name",  "ض Dad — letter name",    11),
    ("letters-ra-to-dad", "daad-letter-sound", "ض Dad — pronunciation",  12),

    # ── Lesson 4 (ط – ي) ──────────────────────────────────────────────────
    ("letters-ta-to-ya", "taa-letter-name",   "ط Tah — letter name",    1),
    ("letters-ta-to-ya", "taa-letter-sound",  "ط Tah — pronunciation",  2),
    ("letters-ta-to-ya", "thaa-letter-name",  "ظ Zah — letter name",    3),
    ("letters-ta-to-ya", "thaa-letter-sound", "ظ Zah — pronunciation",  4),
    ("letters-ta-to-ya", "ayn-letter-name",   "ع Ayn — letter name",    5),
    ("letters-ta-to-ya", "ayn-letter-sound",  "ع Ayn — pronunciation",  6),
    ("letters-ta-to-ya", "ghayn-letter-name", "غ Ghayn — letter name",  7),
    ("letters-ta-to-ya", "ghayn-letter-sound","غ Ghayn — pronunciation",8),
    ("letters-ta-to-ya", "fa-letter-name",    "ف Fa — letter name",     9),
    ("letters-ta-to-ya", "fa-letter-sound",   "ف Fa — pronunciation",   10),
    ("letters-ta-to-ya", "qaf-letter-name",   "ق Qaf — letter name",    11),
    ("letters-ta-to-ya", "qaf-letter-sound",  "ق Qaf — pronunciation",  12),
    ("letters-ta-to-ya", "kaf-letter-name",   "ك Kaf — letter name",    13),
    ("letters-ta-to-ya", "kaf-letter-sound",  "ك Kaf — pronunciation",  14),
    ("letters-ta-to-ya", "lam-letter-name",   "ل Lam — letter name",    15),
    ("letters-ta-to-ya", "lam-letter-sound",  "ل Lam — pronunciation",  16),
    ("letters-ta-to-ya", "miim-letter-name",  "م Mim — letter name",    17),
    ("letters-ta-to-ya", "miim-letter-sound", "م Mim — pronunciation",  18),
    ("letters-ta-to-ya", "nuun-letter-name",  "ن Nun — letter name",    19),
    ("letters-ta-to-ya", "nuun-letter-sound", "ن Nun — pronunciation",  20),
    ("letters-ta-to-ya", "ha-letter-name",    "ه Ha — letter name",     21),
    ("letters-ta-to-ya", "ha-letter-sound",   "ه Ha — pronunciation",   22),
    ("letters-ta-to-ya", "waw-letter-name",   "و Waw — letter name",    23),
    ("letters-ta-to-ya", "waw-letter-sound",  "و Waw — pronunciation",  24),
    ("letters-ta-to-ya", "ya-letter-name",    "ي Ya — letter name",     25),
    ("letters-ta-to-ya", "ya-letter-sound",   "ي Ya — pronunciation",   26),
]

COURSE_SLUG = "arabic-alphabet-mastery"

# Folder relative to this file: ../../../../Arabic-audio/
AUDIO_DIR = Path(__file__).resolve().parents[3] / "Arabic-audio"


class Command(BaseCommand):
    help = "Upload Arabic alphabet audio files to Cloudinary and attach to lessons"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be done without uploading or saving anything.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # ── imports ────────────────────────────────────────────────────────────
        try:
            import cloudinary
            import cloudinary.uploader
        except ImportError:
            raise CommandError(
                "cloudinary package not installed. Run: pip install cloudinary"
            )

        from curriculum.models import Course, Lesson, LessonAttachment

        # ── configure Cloudinary ───────────────────────────────────────────────
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME") or ""
        api_key    = os.environ.get("CLOUDINARY_API_KEY")    or ""
        api_secret = os.environ.get("CLOUDINARY_API_SECRET") or ""

        if not all([cloud_name, api_key, api_secret]):
            raise CommandError(
                "Cloudinary credentials not found. "
                "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET "
                "as environment variables (or in your .env file)."
            )

        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
        )

        # ── fetch course ───────────────────────────────────────────────────────
        try:
            course = Course.objects.get(slug=COURSE_SLUG)
        except Course.DoesNotExist:
            raise CommandError(
                f"Course '{COURSE_SLUG}' not found. "
                "Run `python manage.py seed_demo_content` first."
            )

        self.stdout.write(f"Course: {course.title}")
        self.stdout.write(f"Audio folder: {AUDIO_DIR}\n")

        if not AUDIO_DIR.exists():
            raise CommandError(
                f"Audio folder not found: {AUDIO_DIR}\n"
                "Make sure the Arabic-audio/ folder is inside the project root."
            )

        created = 0
        skipped = 0
        missing = 0

        for lesson_slug, file_stem, title, order in LESSON_AUDIO:
            # Locate the lesson
            try:
                lesson = Lesson.objects.get(course=course, slug=lesson_slug)
            except Lesson.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ Lesson not found: {lesson_slug} — skipping")
                )
                skipped += 1
                continue

            # Skip if attachment with this title already exists on this lesson
            if LessonAttachment.objects.filter(lesson=lesson, title=title).exists():
                self.stdout.write(f"  ✓ Already exists: [{lesson_slug}] {title}")
                skipped += 1
                continue

            # Find the MP3 file
            mp3_path = AUDIO_DIR / f"{file_stem}.mp3"
            if not mp3_path.exists():
                self.stdout.write(
                    self.style.WARNING(f"  ⚠ File not found: {mp3_path.name} — skipping")
                )
                missing += 1
                continue

            if dry_run:
                self.stdout.write(f"  [dry-run] Would upload: {mp3_path.name} → [{lesson_slug}] {title}")
                continue

            # Upload to Cloudinary (resource_type='video' is used for audio too)
            self.stdout.write(f"  ↑ Uploading {mp3_path.name} …", ending="")
            try:
                result = cloudinary.uploader.upload(
                    str(mp3_path),
                    resource_type="video",
                    folder="learn_arabic/audio/alphabet",
                    public_id=file_stem,
                    overwrite=False,   # don't re-upload if already on Cloudinary
                )
                url = result["secure_url"]
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f" FAILED: {exc}"))
                continue

            # Create the LessonAttachment
            attachment = LessonAttachment(
                lesson=lesson,
                kind=LessonAttachment.Kind.AUDIO,
                title=title,
                external_url=url,
                order=order,
                is_downloadable=True,
            )
            attachment.full_clean()   # runs the file-XOR-url validation
            attachment.save()

            self.stdout.write(self.style.SUCCESS(f" ✓ saved ({lesson_slug})"))
            created += 1

        # ── summary ────────────────────────────────────────────────────────────
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — nothing was saved."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Created: {created} | Already existed: {skipped} | Missing files: {missing}"
                )
            )

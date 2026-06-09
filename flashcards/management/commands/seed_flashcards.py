"""
flashcards/management/commands/seed_flashcards.py

Usage:
    python manage.py seed_flashcards

Creates five Arabic vocabulary flashcard decks and attaches each to the first
suitable published lesson found in the database.  Running the command a second
time is safe — every deck and card is upserted via get_or_create so no
duplicates are created.

Deck catalogue
--------------
  1. Greetings & Expressions   (20 cards) — any lesson, order 1
  2. Numbers 1–20              (20 cards) — any lesson, order 2
  3. Colours                   (12 cards) — any lesson, order 3
  4. Family Members            (14 cards) — any lesson, order 4
  5. Days & Months             (19 cards) — any lesson, order 5

If fewer than five lessons exist the extra decks are attached to whatever
lessons are available (cycling through them).
"""

from django.core.management.base import BaseCommand, CommandError

from curriculum.models import Lesson
from flashcards.models import Flashcard, FlashcardDeck


# ---------------------------------------------------------------------------
# Vocabulary data
# Each entry: (front_arabic, back_english, optional_notes)
# ---------------------------------------------------------------------------

GREETINGS = [
    ("مرحباً", "Hello", "Standard greeting, used any time of day."),
    ("السلام عليكم", "Peace be upon you", "Traditional Islamic greeting."),
    ("وعليكم السلام", "And upon you peace", "Reply to السلام عليكم."),
    ("صباح الخير", "Good morning", ""),
    ("صباح النور", "Good morning (reply)", "Literally 'morning of light'."),
    ("مساء الخير", "Good evening", ""),
    ("مساء النور", "Good evening (reply)", ""),
    ("كيف حالك؟", "How are you?", ""),
    ("بخير، شكراً", "Fine, thank you", ""),
    ("تشرفنا", "Nice to meet you", "Literally 'we are honoured'."),
    ("ما اسمك؟", "What is your name?", ""),
    ("اسمي …", "My name is …", "Fill in with your name."),
    ("من أين أنت؟", "Where are you from?", ""),
    ("أنا من …", "I am from …", ""),
    ("شكراً", "Thank you", ""),
    ("عفواً", "You're welcome / Excuse me", "Context-dependent."),
    ("من فضلك", "Please", ""),
    ("آسف", "Sorry", ""),
    ("مع السلامة", "Goodbye", "Literally 'go in safety'."),
    ("إلى اللقاء", "See you later", ""),
]

NUMBERS = [
    ("صفر", "Zero", ""),
    ("واحد", "One", ""),
    ("اثنان", "Two", "Formal; colloquial often 'اتنين'."),
    ("ثلاثة", "Three", ""),
    ("أربعة", "Four", ""),
    ("خمسة", "Five", ""),
    ("ستة", "Six", ""),
    ("سبعة", "Seven", ""),
    ("ثمانية", "Eight", ""),
    ("تسعة", "Nine", ""),
    ("عشرة", "Ten", ""),
    ("أحد عشر", "Eleven", ""),
    ("اثنا عشر", "Twelve", ""),
    ("ثلاثة عشر", "Thirteen", ""),
    ("أربعة عشر", "Fourteen", ""),
    ("خمسة عشر", "Fifteen", ""),
    ("ستة عشر", "Sixteen", ""),
    ("سبعة عشر", "Seventeen", ""),
    ("ثمانية عشر", "Eighteen", ""),
    ("تسعة عشر", "Nineteen", ""),
    ("عشرون", "Twenty", ""),
]

COLOURS = [
    ("أحمر", "Red", ""),
    ("أزرق", "Blue", ""),
    ("أخضر", "Green", ""),
    ("أصفر", "Yellow", ""),
    ("أبيض", "White", ""),
    ("أسود", "Black", ""),
    ("برتقالي", "Orange", "From the word برتقال (orange fruit)."),
    ("بنفسجي", "Purple / Violet", "From بنفسج, violet flower."),
    ("وردي", "Pink", "From وردة, rose."),
    ("بني", "Brown", ""),
    ("رمادي", "Grey", "From رماد, ash."),
    ("ذهبي", "Golden", "From ذهب, gold."),
    ("فضي", "Silver", "From فضة, silver."),
]

FAMILY = [
    ("أب", "Father", ""),
    ("أم", "Mother", ""),
    ("أخ", "Brother", ""),
    ("أخت", "Sister", ""),
    ("ابن", "Son", ""),
    ("ابنة", "Daughter", "Also بنت in colloquial speech."),
    ("جد", "Grandfather", ""),
    ("جدة", "Grandmother", ""),
    ("عم", "Paternal uncle", "Father's brother."),
    ("خال", "Maternal uncle", "Mother's brother."),
    ("عمة", "Paternal aunt", "Father's sister."),
    ("خالة", "Maternal aunt", "Mother's sister."),
    ("ابن عم", "Male cousin (paternal)", ""),
    ("زوج", "Husband", ""),
    ("زوجة", "Wife", ""),
]

DAYS_MONTHS = [
    # Days
    ("الأحد", "Sunday", "First day of the week in many Arab countries."),
    ("الاثنين", "Monday", ""),
    ("الثلاثاء", "Tuesday", ""),
    ("الأربعاء", "Wednesday", ""),
    ("الخميس", "Thursday", ""),
    ("الجمعة", "Friday", "The holy day of congregational prayer."),
    ("السبت", "Saturday", ""),
    # Months (Modern Standard Arabic)
    ("يناير", "January", ""),
    ("فبراير", "February", ""),
    ("مارس", "March", ""),
    ("أبريل", "April", ""),
    ("مايو", "May", ""),
    ("يونيو", "June", ""),
    ("يوليو", "July", ""),
    ("أغسطس", "August", ""),
    ("سبتمبر", "September", ""),
    ("أكتوبر", "October", ""),
    ("نوفمبر", "November", ""),
    ("ديسمبر", "December", ""),
]

DECKS = [
    {
        "title": "Greetings & Expressions",
        "description": (
            "Essential phrases for everyday Arabic conversations — "
            "how to say hello, goodbye, and polite expressions."
        ),
        "cards": GREETINGS,
    },
    {
        "title": "Numbers 0–20",
        "description": (
            "Cardinal numbers from zero to twenty. "
            "Master these to count, give your phone number, and tell the time."
        ),
        "cards": NUMBERS,
    },
    {
        "title": "Colours",
        "description": (
            "Arabic colour adjectives. "
            "Note: adjectives agree in gender with the noun they describe."
        ),
        "cards": COLOURS,
    },
    {
        "title": "Family Members",
        "description": (
            "Vocabulary for family relationships. "
            "Arabic distinguishes maternal vs paternal relatives — pay attention!"
        ),
        "cards": FAMILY,
    },
    {
        "title": "Days of the Week & Months",
        "description": (
            "All seven days and twelve Gregorian months in Modern Standard Arabic."
        ),
        "cards": DAYS_MONTHS,
    },
]


class Command(BaseCommand):
    help = "Seed flashcard decks with Arabic vocabulary. Safe to run multiple times."

    def handle(self, *args, **options):
        # Fetch published lessons, ordered by course level then lesson order.
        lessons = list(
            Lesson.objects
            .select_related("course", "course__level")
            .filter(course__is_published=True)
            .order_by(
                "course__level__order",
                "course__id",
                "order",
            )
        )

        if not lessons:
            raise CommandError(
                "No published lessons found. "
                "Run the curriculum seed first, or publish at least one lesson."
            )

        created_decks = 0
        created_cards = 0

        for i, deck_spec in enumerate(DECKS):
            # Cycle through available lessons if there are fewer than 5.
            lesson = lessons[i % len(lessons)]

            deck, deck_created = FlashcardDeck.objects.get_or_create(
                lesson=lesson,
                title=deck_spec["title"],
                defaults={
                    "description": deck_spec["description"],
                    "is_published": True,
                },
            )

            if deck_created:
                created_decks += 1
                self.stdout.write(
                    f"  ✓ Created deck: \"{deck.title}\" "
                    f"→ {lesson.course.title} / {lesson.title}"
                )
            else:
                self.stdout.write(
                    f"  · Deck already exists: \"{deck.title}\" — updating cards"
                )

            for order, (front, back, notes) in enumerate(deck_spec["cards"], start=1):
                card, card_created = Flashcard.objects.get_or_create(
                    deck=deck,
                    order=order,
                    defaults={
                        "front": front,
                        "back": back,
                        "front_lang": "ar",
                        "back_lang": "en",
                        "notes": notes,
                    },
                )
                if card_created:
                    created_cards += 1
                else:
                    # Keep content fresh if the card already exists.
                    updated = False
                    for field, value in [
                        ("front", front),
                        ("back", back),
                        ("notes", notes),
                    ]:
                        if getattr(card, field) != value:
                            setattr(card, field, value)
                            updated = True
                    if updated:
                        card.save(update_fields=["front", "back", "notes"])

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. {created_decks} deck(s) and {created_cards} card(s) created."
        ))
        self.stdout.write(
            "Run  python manage.py seed_flashcards  again any time — it is idempotent."
        )

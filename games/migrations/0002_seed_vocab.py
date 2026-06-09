"""
Data migration: seed VocabWord and GameQuestion rows from the content
that was previously hardcoded inside the game templates.

All words are tagged as A1 level (order=1). If your levels table uses
different PKs, change `level_code = "A1"` below — we look up by code,
not by PK, so it works regardless of auto-increment values.
"""

from django.db import migrations


# ── Hardcoded data (mirrors the JS arrays in the templates) ──────────

VOCAB_WORDS = [
    # Word Builder + Match Pairs core set (A1)
    {
        "arabic": "كِتَاب", "english": "Book", "emoji": "📚", "phonetic": "kitāb",
        "letters": ["ك", "ت", "ا", "ب"],
        "context_forms": ["كـ", "ـتـ", "ـا", "ب"],
        "missing_index": 1, "wrong_choices": ["ن", "م"],
    },
    {
        "arabic": "بَيْت", "english": "House", "emoji": "🏠", "phonetic": "bayt",
        "letters": ["ب", "ي", "ت"],
        "context_forms": ["بـ", "ـيـ", "ت"],
        "missing_index": 1, "wrong_choices": ["ا", "و"],
    },
    {
        "arabic": "مَاء", "english": "Water", "emoji": "💧", "phonetic": "māʾ",
        "letters": ["م", "ا", "ء"],
        "context_forms": ["مـ", "ـا", "ء"],
        "missing_index": 0, "wrong_choices": ["ب", "ت"],
    },
    {
        "arabic": "شَمْس", "english": "Sun", "emoji": "☀️", "phonetic": "shams",
        "letters": ["ش", "م", "س"],
        "context_forms": ["شـ", "ـمـ", "ـس"],
        "missing_index": 2, "wrong_choices": ["ن", "ر"],
    },
    {
        "arabic": "قَمَر", "english": "Moon", "emoji": "🌙", "phonetic": "qamar",
        "letters": ["ق", "م", "ر"],
        "context_forms": ["قـ", "ـمـ", "ـر"],
        "missing_index": 1, "wrong_choices": ["ب", "ك"],
    },
    {
        "arabic": "كَلْب", "english": "Dog", "emoji": "🐕", "phonetic": "kalb",
        "letters": ["ك", "ل", "ب"],
        "context_forms": ["كـ", "ـلـ", "ـب"],
        "missing_index": 1, "wrong_choices": ["ن", "م"],
    },
    {
        "arabic": "قِطَّة", "english": "Cat", "emoji": "🐈", "phonetic": "qiṭṭa",
        "letters": ["ق", "ط", "ة"],
        "context_forms": ["قـ", "ـطـ", "ـة"],
        "missing_index": 0, "wrong_choices": ["ك", "ب"],
    },
    {
        "arabic": "تُفَّاحَة", "english": "Apple", "emoji": "🍎", "phonetic": "tuffāḥa",
        "letters": ["ت", "ف", "ا", "ح", "ة"],
        "context_forms": ["تـ", "ـفـ", "ـا", "ـحـ", "ـة"],
        "missing_index": 1, "wrong_choices": ["ك", "ب"],
    },
    {
        "arabic": "مَدْرَسَة", "english": "School", "emoji": "🏫", "phonetic": "madrasa",
        "letters": ["م", "د", "ر", "س", "ة"],
        "context_forms": ["مـ", "ـد", "ر", "ـسـ", "ـة"],
        "missing_index": 2, "wrong_choices": ["ب", "ن"],
    },
    {
        "arabic": "سَيَّارَة", "english": "Car", "emoji": "🚗", "phonetic": "sayyāra",
        "letters": ["س", "ي", "ا", "ر", "ة"],
        "context_forms": ["سـ", "ـيـ", "ـا", "ـرـ", "ـة"],
        "missing_index": 3, "wrong_choices": ["ب", "ك"],
    },
    {
        "arabic": "طَائِرَة", "english": "Airplane", "emoji": "✈️", "phonetic": "ṭāʾira",
        "letters": ["ط", "ا", "ئ", "ر", "ة"],
        "context_forms": ["طـ", "ـا", "ـئـ", "ـرـ", "ـة"],
        "missing_index": 0, "wrong_choices": ["ب", "ك"],
    },
    {
        "arabic": "وَلَد", "english": "Boy", "emoji": "👦", "phonetic": "walad",
        "letters": ["و", "ل", "د"],
        "context_forms": ["و", "ـلـ", "ـد"],
        "missing_index": 1, "wrong_choices": ["ب", "ن"],
    },
    {
        "arabic": "بِنْت", "english": "Girl", "emoji": "👧", "phonetic": "bint",
        "letters": ["ب", "ن", "ت"],
        "context_forms": ["بـ", "ـنـ", "ـت"],
        "missing_index": 1, "wrong_choices": ["ل", "م"],
    },
    {
        "arabic": "أُسْتَاذ", "english": "Teacher", "emoji": "👨‍🏫", "phonetic": "ustādh",
        "letters": ["أ", "س", "ت", "ا", "ذ"],
        "context_forms": ["أـ", "ـسـ", "ـتـ", "ـا", "ذ"],
        "missing_index": 1, "wrong_choices": ["ب", "ن"],
    },
    {
        "arabic": "قَلَم", "english": "Pen", "emoji": "🖊️", "phonetic": "qalam",
        "letters": ["ق", "ل", "م"],
        "context_forms": ["قـ", "ـلـ", "ـم"],
        "missing_index": 2, "wrong_choices": ["ب", "ن"],
    },
    {
        "arabic": "بَاب", "english": "Door", "emoji": "🚪", "phonetic": "bāb",
        "letters": ["ب", "ا", "ب"],
        "context_forms": ["بـ", "ـا", "ب"],
        "missing_index": 0, "wrong_choices": ["ك", "ت"],
    },
    # Extra match-pairs words (no letter data needed)
    {"arabic": "شَجَرَة", "english": "Tree",   "emoji": "🌳", "phonetic": "shajara"},
    {"arabic": "وَرْدَة",  "english": "Rose",   "emoji": "🌹", "phonetic": "warda"},
    {"arabic": "سَمَكَة", "english": "Fish",   "emoji": "🐟", "phonetic": "samaka"},
    {"arabic": "طَاوِلَة","english": "Table",  "emoji": "🪑", "phonetic": "ṭāwila"},
    {"arabic": "نَافِذَة","english": "Window", "emoji": "🪟", "phonetic": "nāfidha"},
    {"arabic": "مِفْتَاح","english": "Key",    "emoji": "🔑", "phonetic": "miftāḥ"},
    {"arabic": "حَقِيبَة","english": "Bag",    "emoji": "🎒", "phonetic": "ḥaqība"},
    {"arabic": "هَاتِف",  "english": "Phone",  "emoji": "📱", "phonetic": "hātif"},
]

SENTENCE_BUILDER_QUESTIONS = [
    {"arabic_sentence": "أنا أذهب إلى المدرسة", "english_sentence": "I go to school",
     "word_tokens": ["أنا", "أذهب", "إلى", "المدرسة"]},
    {"arabic_sentence": "هذا كتاب جديد", "english_sentence": "This is a new book",
     "word_tokens": ["هذا", "كتاب", "جديد"]},
    {"arabic_sentence": "البيت كبير وجميل", "english_sentence": "The house is big and beautiful",
     "word_tokens": ["البيت", "كبير", "وجميل"]},
    {"arabic_sentence": "أنا أحب القراءة", "english_sentence": "I love reading",
     "word_tokens": ["أنا", "أحب", "القراءة"]},
    {"arabic_sentence": "الشمس تشرق في الصباح", "english_sentence": "The sun rises in the morning",
     "word_tokens": ["الشمس", "تشرق", "في", "الصباح"]},
    {"arabic_sentence": "الماء بارد ولذيذ", "english_sentence": "The water is cold and delicious",
     "word_tokens": ["الماء", "بارد", "ولذيذ"]},
    {"arabic_sentence": "الولد يلعب في الحديقة", "english_sentence": "The boy plays in the garden",
     "word_tokens": ["الولد", "يلعب", "في", "الحديقة"]},
    {"arabic_sentence": "القطة تنام على الأريكة", "english_sentence": "The cat sleeps on the sofa",
     "word_tokens": ["القطة", "تنام", "على", "الأريكة"]},
    {"arabic_sentence": "أنا أشرب الماء", "english_sentence": "I drink water",
     "word_tokens": ["أنا", "أشرب", "الماء"]},
    {"arabic_sentence": "المدرسة قريبة من البيت", "english_sentence": "The school is near the house",
     "word_tokens": ["المدرسة", "قريبة", "من", "البيت"]},
    {"arabic_sentence": "الطفل يأكل التفاح", "english_sentence": "The child eats the apple",
     "word_tokens": ["الطفل", "يأكل", "التفاح"]},
    {"arabic_sentence": "أنا أكتب بالقلم", "english_sentence": "I write with the pen",
     "word_tokens": ["أنا", "أكتب", "بالقلم"]},
]

TRUE_OR_FALSE_QUESTIONS = [
    {"arabic_sentence": "الكتاب أداة للقراءة",   "english_sentence": "A book is a reading tool",   "emoji": "📚", "is_true": True},
    {"arabic_sentence": "الكلب يطير في السماء",   "english_sentence": "The dog flies in the sky",   "emoji": "🐕", "is_true": False},
    {"arabic_sentence": "الشمس تضيء النهار",      "english_sentence": "The sun lights the day",     "emoji": "☀️", "is_true": True},
    {"arabic_sentence": "الماء يأكل الطعام",       "english_sentence": "Water eats food",            "emoji": "💧", "is_true": False},
    {"arabic_sentence": "البيت مكان للسكن",        "english_sentence": "A house is a place to live", "emoji": "🏠", "is_true": True},
    {"arabic_sentence": "القمر يظهر في الليل",     "english_sentence": "The moon appears at night",  "emoji": "🌙", "is_true": True},
    {"arabic_sentence": "الطائرة تسبح في البحر",   "english_sentence": "The airplane swims in the sea", "emoji": "✈️", "is_true": False},
    {"arabic_sentence": "الأستاذ يعلّم الطلاب",    "english_sentence": "The teacher teaches students", "emoji": "👨‍🏫", "is_true": True},
    {"arabic_sentence": "القلم يُستخدم للكتابة",   "english_sentence": "A pen is used for writing",  "emoji": "🖊️", "is_true": True},
    {"arabic_sentence": "القطة تنبح مثل الكلب",    "english_sentence": "The cat barks like a dog",   "emoji": "🐈", "is_true": False},
    {"arabic_sentence": "السيارة تسير على الطريق", "english_sentence": "The car drives on the road", "emoji": "🚗", "is_true": True},
    {"arabic_sentence": "التفاحة نوع من الخضروات","english_sentence": "An apple is a type of vegetable", "emoji": "🍎", "is_true": False},
]


def seed_vocab(apps, schema_editor):
    VocabWord    = apps.get_model("games", "VocabWord")
    GameQuestion = apps.get_model("games", "GameQuestion")
    Level        = apps.get_model("curriculum", "Level")

    # Try to find A1 level; if it doesn't exist yet, leave level=None
    try:
        a1 = Level.objects.get(code="A1")
    except Level.DoesNotExist:
        a1 = None

    for w in VOCAB_WORDS:
        VocabWord.objects.get_or_create(
            arabic=w["arabic"],
            defaults={
                "english":       w.get("english", ""),
                "emoji":         w.get("emoji", ""),
                "phonetic":      w.get("phonetic", ""),
                "letters":       w.get("letters", []),
                "context_forms": w.get("context_forms", []),
                "missing_index": w.get("missing_index"),
                "wrong_choices": w.get("wrong_choices", []),
                "level":         a1,
                "is_active":     True,
            },
        )

    for q in SENTENCE_BUILDER_QUESTIONS:
        GameQuestion.objects.get_or_create(
            arabic_sentence=q["arabic_sentence"],
            game_type="sentence_builder",
            defaults={
                "english_sentence": q.get("english_sentence", ""),
                "word_tokens":      q.get("word_tokens", []),
                "level":            a1,
                "is_active":        True,
            },
        )

    for q in TRUE_OR_FALSE_QUESTIONS:
        GameQuestion.objects.get_or_create(
            arabic_sentence=q["arabic_sentence"],
            game_type="true_or_false",
            defaults={
                "english_sentence": q.get("english_sentence", ""),
                "emoji":            q.get("emoji", ""),
                "is_true":          q.get("is_true"),
                "level":            a1,
                "is_active":        True,
            },
        )


def unseed_vocab(apps, schema_editor):
    # Reverse: delete only rows we created (match by arabic text)
    VocabWord    = apps.get_model("games", "VocabWord")
    GameQuestion = apps.get_model("games", "GameQuestion")
    arabics = [w["arabic"] for w in VOCAB_WORDS]
    VocabWord.objects.filter(arabic__in=arabics).delete()
    sentences = [q["arabic_sentence"] for q in SENTENCE_BUILDER_QUESTIONS + TRUE_OR_FALSE_QUESTIONS]
    GameQuestion.objects.filter(arabic_sentence__in=sentences).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0001_initial"),
        ("curriculum", "0002_seed_levels"),   # ensures A1 level exists
    ]

    operations = [
        migrations.RunPython(seed_vocab, unseed_vocab),
    ]

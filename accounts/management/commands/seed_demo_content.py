"""
Management command: seed_demo_content

Creates:
  1. A demo teacher account
  2. Three rich A1 courses with 4-5 lessons each
  3. Enrolls the demo student in all three courses
  4. Marks several lessons as completed so dashboard shows real progress
  5. Adds extra A1 vocabulary words for richer games

Run:  python manage.py seed_demo_content
Safe to re-run — uses get_or_create throughout.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify


# ── Course / lesson content ──────────────────────────────────────────────────

COURSES = [
    {
        "title":       "Arabic Alphabet Mastery",
        "slug":        "arabic-alphabet-mastery",
        "description": (
            "Start your Arabic journey by mastering all 28 letters of the alphabet. "
            "Learn how each letter sounds, how it changes shape depending on its position "
            "in a word, and how to write your first Arabic words. No prior knowledge needed."
        ),
        "what_you_learn": "Read every Arabic letter · Write basic words · Recognise letter shapes",
        "lessons": [
            {
                "order": 1, "title": "Welcome to Arabic", "slug": "welcome-to-arabic",
                "duration_minutes": 8,
                "body_markdown": """## Welcome to Arabic! 🎉

Arabic is spoken by over **400 million people** across 22 countries. It is the language of the Quran, science, poetry, and rich civilisations.

### Why learn Arabic?
- Connect with Arab culture and people
- Understand Quranic Arabic
- Open doors to the Middle East and North Africa

### The Arabic alphabet
Arabic has **28 letters**. It is written **right to left** ← and is a beautiful, flowing script.

> **Fun fact:** Arabic gave English words like *algebra*, *coffee*, *sugar*, and *algorithm*!

### Your first Arabic word
Let's start with the word for "Hello":

| Arabic | Transliteration | Meaning |
|--------|----------------|---------|
| مَرْحَبًا | Mar-ha-ban | Hello / Welcome |

Say it out loud: **Mar-ha-ban** 👋

In the next lesson we'll learn the first 7 letters of the alphabet.""",
            },
            {
                "order": 2, "title": "Letters ا to ذ — The First Group", "slug": "letters-alef-to-thal",
                "duration_minutes": 12,
                "body_markdown": """## The First 7 Letters

These are the first 7 letters of the Arabic alphabet. Study each one carefully.

| Letter | Name | Sound | Example word |
|--------|------|-------|-------------|
| ا | Alef | 'a' / long vowel | أَب (ab) — Father |
| ب | Ba | 'b' | بَيْت (bayt) — House |
| ت | Ta | 't' | تُفَّاحَة (tuffāḥa) — Apple |
| ث | Tha | 'th' (as in *think*) | ثَلْج (thalj) — Snow |
| ج | Jim | 'j' | جَمَل (jamal) — Camel |
| ح | Ha | strong 'h' (from throat) | حَلِيب (ḥalīb) — Milk |
| خ | Kha | 'kh' (like Scottish *loch*) | خُبْز (khubz) — Bread |

### Letter shapes
Each letter has up to **4 shapes** depending on where it appears in a word:
- **Isolated** — standing alone
- **Initial** — at the start of a word
- **Medial** — in the middle
- **Final** — at the end

### Practice
Write each letter 5 times. Focus on the strokes — Arabic letters are drawn in specific directions.

> 💡 **Tip:** Use the Games section to practise building words with these letters!""",
            },
            {
                "order": 3, "title": "Letters ر to ض — The Second Group", "slug": "letters-ra-to-dad",
                "duration_minutes": 12,
                "body_markdown": """## The Second Group of Letters

| Letter | Name | Sound | Example word |
|--------|------|-------|-------------|
| ر | Ra | 'r' (rolled slightly) | رَجُل (rajul) — Man |
| ز | Zay | 'z' | زَيْت (zayt) — Oil |
| س | Sin | 's' | سَمَكَة (samaka) — Fish |
| ش | Shin | 'sh' | شَمْس (shams) — Sun |
| ص | Sad | emphatic 's' | صَابُون (ṣābūn) — Soap |
| ض | Dad | emphatic 'd' | ضَوْء (ḍawʾ) — Light |

### The emphatic letters
Arabic has a set of **emphatic (heavy) consonants** — ص، ض، ط، ظ — that are pronounced deeper in the mouth. They change the sound of surrounding vowels, making them deeper.

This is one of the unique beauties of Arabic!

### Quick Quiz
Which letter makes the **'sh'** sound?
- ا
- ش ✅
- س
- ص

Well done if you picked **ش (Shin)**!""",
            },
            {
                "order": 4, "title": "Letters ط to ي — Completing the Alphabet", "slug": "letters-ta-to-ya",
                "duration_minutes": 14,
                "body_markdown": """## The Final Letters — You're Almost There! 🏁

| Letter | Name | Sound | Example word |
|--------|------|-------|-------------|
| ط | Ta | emphatic 't' | طَاوِلَة (ṭāwila) — Table |
| ظ | Dha | emphatic 'th' | ظَلَام (ẓalām) — Darkness |
| ع | Ayn | voiced pharyngeal (unique to Arabic!) | عَيْن (ʿayn) — Eye |
| غ | Ghayn | 'gh' (like French 'r') | غُرْفَة (ghurfa) — Room |
| ف | Fa | 'f' | فِيل (fīl) — Elephant |
| ق | Qaf | deep 'q' from back of throat | قَمَر (qamar) — Moon |
| ك | Kaf | 'k' | كِتَاب (kitāb) — Book |
| ل | Lam | 'l' | لَيْل (layl) — Night |
| م | Mim | 'm' | مَاء (māʾ) — Water |
| ن | Nun | 'n' | نَجْمَة (najma) — Star |
| ه | Ha | soft 'h' | هَاتِف (hātif) — Phone |
| و | Waw | 'w' / long 'oo' | وَرْدَة (warda) — Rose |
| ي | Ya | 'y' / long 'ee' | يَد (yad) — Hand |

### Congratulations! 🎊
You now know all **28 letters** of the Arabic alphabet.

> 🎯 **Challenge:** Head to the **Word Builder** game and try to spell as many words as you can using your new knowledge!""",
            },
            {
                "order": 5, "title": "Reading Your First Arabic Sentences", "slug": "reading-first-sentences",
                "duration_minutes": 10,
                "body_markdown": """## Reading Arabic — Putting It All Together

Now that you know all 28 letters, let's read some real sentences!

### Everyday greetings

| Arabic | Transliteration | Meaning |
|--------|----------------|---------|
| مَرْحَبًا | Marḥaban | Hello |
| السَّلَامُ عَلَيْكُم | As-salāmu ʿalaykum | Peace be upon you |
| وَعَلَيْكُم السَّلَام | Wa ʿalaykum as-salām | And upon you peace |
| كَيْفَ حَالُكَ؟ | Kayfa ḥāluk? | How are you? |
| بِخَيْر، شُكْرًا | Bikhair, shukran | Fine, thank you |
| مَعَ السَّلَامَة | Maʿa as-salāma | Goodbye |

### Numbers 1–10

| Number | Arabic | Transliteration |
|--------|--------|----------------|
| 1 | وَاحِد | wāḥid |
| 2 | اثْنَان | ithnān |
| 3 | ثَلَاثَة | thalātha |
| 4 | أَرْبَعَة | arbaʿa |
| 5 | خَمْسَة | khamsa |
| 6 | سِتَّة | sitta |
| 7 | سَبْعَة | sabʿa |
| 8 | ثَمَانِيَة | thamāniya |
| 9 | تِسْعَة | tisʿa |
| 10 | عَشَرَة | ʿashara |

### You've completed the Alphabet course! 🏆
Move on to **Everyday Conversations** to start speaking Arabic right away.""",
            },
        ],
    },
    {
        "title":       "Everyday Conversations",
        "slug":        "everyday-conversations",
        "description": (
            "Learn the Arabic phrases you'll actually use — greetings, introductions, "
            "shopping, ordering food, and asking for directions. "
            "Build real confidence to communicate from day one."
        ),
        "what_you_learn": "Greet people · Introduce yourself · Handle everyday situations",
        "lessons": [
            {
                "order": 1, "title": "Greetings & Introductions", "slug": "greetings-introductions",
                "duration_minutes": 10,
                "body_markdown": """## Greetings & Introductions 👋

### Islamic greeting
The most common greeting in Arabic-speaking countries:

**السَّلَامُ عَلَيْكُم** — *As-salāmu ʿalaykum* — "Peace be upon you"

Response: **وَعَلَيْكُم السَّلَام** — *Wa ʿalaykum as-salām*

### Introducing yourself

| Arabic | Transliteration | English |
|--------|----------------|---------|
| اسْمِي... | Ismī... | My name is... |
| أَنَا مِن... | Anā min... | I am from... |
| يَسْعَدُنِي بِمَعْرِفَتِك | Yasʿadunī bimaʿrifatik | Nice to meet you |
| كَمْ عُمْرُكَ؟ | Kam ʿumruk? | How old are you? |
| عُمْرِي... سَنَة | ʿUmrī... sana | I am ... years old |

### Dialogue practice
> **Ali:** السَّلَامُ عَلَيْكُم!
> **Sara:** وَعَلَيْكُم السَّلَام! كَيْفَ حَالُكَ؟
> **Ali:** بِخَيْر، شُكْرًا. اسْمِي عَلِي. وَأَنْتِ؟
> **Sara:** اسْمِي سَارَة. يَسْعَدُنِي بِمَعْرِفَتِك!

Translation:
> **Ali:** Peace be upon you!
> **Sara:** And upon you peace! How are you?
> **Ali:** Fine, thank you. My name is Ali. And you?
> **Sara:** My name is Sara. Nice to meet you!""",
            },
            {
                "order": 2, "title": "Family & Relationships", "slug": "family-relationships",
                "duration_minutes": 12,
                "body_markdown": """## Family Vocabulary 👨‍👩‍👧‍👦

| Arabic | Transliteration | English |
|--------|----------------|---------|
| أُسْرَة | usra | Family |
| أَب | ab | Father |
| أُمّ | umm | Mother |
| أَخ | akh | Brother |
| أُخْت | ukht | Sister |
| جَدّ | jadd | Grandfather |
| جَدَّة | jadda | Grandmother |
| عَمّ | ʿamm | Uncle (paternal) |
| خَال | khāl | Uncle (maternal) |
| ابْن | ibn | Son |
| بِنْت | bint | Daughter |
| زَوْج | zawj | Husband |
| زَوْجَة | zawja | Wife |

### Talking about family

| Arabic | English |
|--------|---------|
| هَلْ عِنْدَكَ إِخْوَة؟ | Do you have siblings? |
| عِنْدِي أَخٌ وَأُخْتَان | I have a brother and two sisters |
| أُسْرَتِي كَبِيرَة | My family is big |
| أُسْرَتِي صَغِيرَة | My family is small |

### Cultural note 🌍
In Arab culture, family is central to life. It's very common to ask about family when meeting someone new — it's a sign of warmth and interest, not intrusion!""",
            },
            {
                "order": 3, "title": "At the Market — Shopping & Numbers", "slug": "at-the-market",
                "duration_minutes": 15,
                "body_markdown": """## Shopping in Arabic 🛒

### Useful phrases

| Arabic | Transliteration | English |
|--------|----------------|---------|
| بِكَمْ هَذَا؟ | Bikam hādhā? | How much is this? |
| غَالٍ جِدًّا | Ghālī jiddan | Very expensive |
| رَخِيص | rakhīṣ | Cheap |
| هَلْ عِنْدَكَ...؟ | Hal ʿindak...? | Do you have...? |
| أُرِيدُ... | Urīdu... | I want... |
| مِنْ فَضْلِكَ | Min faḍlik | Please |
| شُكْرًا | Shukran | Thank you |
| عَفْوًا | ʿAfwan | You're welcome / Excuse me |

### Food vocabulary

| Arabic | English |
|--------|---------|
| خُبْز | Bread |
| لَحْم | Meat |
| دَجَاج | Chicken |
| سَمَك | Fish |
| أَرُزّ | Rice |
| خُضْرَوَات | Vegetables |
| فَاكِهَة | Fruit |
| مَاء | Water |
| عَصِير | Juice |
| قَهْوَة | Coffee |
| شَاي | Tea |

### Sample conversation at a market
> **Customer:** مَرْحَبًا! بِكَمْ الْخُبْز؟
> **Seller:** دِرْهَمَان فَقَط!
> **Customer:** أُرِيدُ اثْنَيْن مِنْ فَضْلِكَ
> **Seller:** تَفَضَّل! شُكْرًا!

> Hello! How much is the bread? — Just two dirhams! — I want two please — Here you go! Thank you!""",
            },
            {
                "order": 4, "title": "Colours, Directions & Weather", "slug": "colours-directions-weather",
                "duration_minutes": 12,
                "body_markdown": """## Colours 🎨

| Arabic | Transliteration | Colour |
|--------|----------------|--------|
| أَحْمَر | aḥmar | Red 🔴 |
| أَزْرَق | azraq | Blue 🔵 |
| أَخْضَر | akhḍar | Green 🟢 |
| أَصْفَر | aṣfar | Yellow 🟡 |
| أَبْيَض | abyaḍ | White ⬜ |
| أَسْوَد | aswad | Black ⬛ |
| بُرْتُقَالِي | burtuqālī | Orange 🟠 |
| بَنَفْسَجِي | banafsajī | Purple 🟣 |

## Directions 🧭

| Arabic | English |
|--------|---------|
| يَمِين | Right |
| يَسَار | Left |
| أَمَام | Straight ahead |
| وَرَاء | Behind |
| قَرِيب | Near |
| بَعِيد | Far |
| أَيْنَ...؟ | Where is...? |

## Weather ☁️

| Arabic | English |
|--------|---------|
| الطَّقْس جَمِيل | The weather is beautiful |
| حَارّ | Hot |
| بَارِد | Cold |
| مُشْمِس | Sunny |
| مُمْطِر | Rainy |
| يَتْقُر | It's snowing |""",
            },
        ],
    },
    {
        "title":       "Islamic Arabic Essentials",
        "slug":        "islamic-arabic-essentials",
        "description": (
            "Understand the Arabic of the Quran, daily prayers, and Islamic vocabulary. "
            "Learn the meaning behind the words you say every day — from Bismillah to "
            "Alhamdulillah — and deepen your connection to your faith."
        ),
        "what_you_learn": "Understand prayer words · Quran vocabulary · Islamic phrases",
        "lessons": [
            {
                "order": 1, "title": "The Language of the Quran", "slug": "language-of-quran",
                "duration_minutes": 10,
                "body_markdown": """## Why Learn Quranic Arabic? 📖

The Quran was revealed in **Classical Arabic** — one of the most precise and expressive languages ever written. Understanding even a few words of Arabic can transform your relationship with the Quran and your prayers.

### The most important phrase

**بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ**
*Bismillāhi r-raḥmāni r-raḥīm*
**"In the name of Allah, the Most Gracious, the Most Merciful"**

Let's break it down:
| Word | Meaning |
|------|---------|
| بِسْمِ | In the name of |
| اللَّه | Allah (God) |
| الرَّحْمَن | The Most Gracious (vast mercy) |
| الرَّحِيم | The Most Merciful (specific mercy) |

### The root system
Arabic is built on **3-letter roots**. For example, the root **ر-ح-م** (r-ḥ-m) relates to mercy:
- رَحْمَة — mercy
- رَحِيم — merciful
- رَحْمَن — most gracious
- مَرْحَبًا — welcome (rooted in making space / showing mercy)

This root system is one of the most beautiful features of Arabic — once you learn a root, you unlock dozens of related words!""",
            },
            {
                "order": 2, "title": "Daily Dhikr & Phrases", "slug": "daily-dhikr-phrases",
                "duration_minutes": 12,
                "body_markdown": """## Essential Islamic Phrases 🤲

These phrases are used by Muslims daily. Understanding their meaning deepens every moment.

### The core phrases

| Arabic | Transliteration | Meaning | When used |
|--------|----------------|---------|-----------|
| بِسْمِ اللَّه | Bismillāh | In the name of Allah | Before any action |
| الْحَمْدُ لِلَّه | Alḥamdulillāh | All praise is for Allah | Gratitude, after eating/sneezing |
| سُبْحَانَ اللَّه | Subḥānallāh | Glory be to Allah | Wonder, amazement |
| اللَّهُ أَكْبَر | Allāhu Akbar | Allah is the Greatest | Adhan, prayer, moments of awe |
| إِنْ شَاءَ اللَّه | Inshāʾallāh | If Allah wills | Future plans |
| مَاشَاءَ اللَّه | Māshāʾallāh | What Allah has willed | Admiring something beautiful |
| جَزَاكَ اللَّه خَيْرًا | Jazākallāh khayran | May Allah reward you | Expressing gratitude |
| أَسْتَغْفِرُ اللَّه | Astaghfirullāh | I seek Allah's forgiveness | Seeking forgiveness |

### Word breakdown: الْحَمْدُ لِلَّه
| Word | Root | Meaning |
|------|------|---------|
| الْحَمْد | ح-م-د | Praise, gratitude |
| لِ | — | For / belongs to |
| اللَّه | — | Allah |

> Together: **"All praise and gratitude belongs to Allah"** — said in thankfulness for every blessing, big or small.""",
            },
            {
                "order": 3, "title": "The Five Pillars in Arabic", "slug": "five-pillars-arabic",
                "duration_minutes": 14,
                "body_markdown": """## The Five Pillars — أَرْكَانُ الإِسْلَام 🕌

**أَرْكَان** (arkān) means pillars or foundations.

### 1. الشَّهَادَة — Ash-Shahāda (The Declaration of Faith)

**لَا إِلَهَ إِلَّا اللَّهُ مُحَمَّدٌ رَسُولُ اللَّه**
*Lā ilāha illallāhu Muḥammadun rasūlullāh*
**"There is no god but Allah, and Muhammad is the messenger of Allah"**

| Word | Meaning |
|------|---------|
| لَا | No / None |
| إِلَه | God / deity |
| إِلَّا | Except |
| رَسُول | Messenger |

### 2. الصَّلَاة — Aṣ-Ṣalāh (Prayer)
Five daily prayers. The Arabic word صَلَاة comes from the root ص-ل-و meaning connection.

### 3. الزَّكَاة — Az-Zakāh (Charity)
From the root ز-ك-و meaning purification and growth.

### 4. الصَّوْم — Aṣ-Ṣawm (Fasting)
Fasting during Ramadan. رَمَضَان comes from the root ر-م-ض meaning intense heat.

### 5. الحَجّ — Al-Ḥajj (Pilgrimage)
The journey to Makkah. الكَعْبَة (Al-Kaʿba) is the sacred house of Allah.

> 🌟 Learning the Arabic behind these pillars transforms your understanding of Islam!""",
            },
            {
                "order": 4, "title": "Surah Al-Fatiha — Word by Word", "slug": "surah-al-fatiha",
                "duration_minutes": 20,
                "body_markdown": """## Sūrat Al-Fātiḥa — The Opening Chapter 📖

Al-Fatiha is the most recited chapter in the Quran — said at least **17 times daily** in prayer. Let's understand every word.

---

### بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ
*Bismillāhi r-raḥmāni r-raḥīm*
In the name of Allah, the Most Gracious, the Most Merciful

---

### الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ
*Al-ḥamdu lillāhi rabbi l-ʿālamīn*

| Word | Meaning |
|------|---------|
| الْحَمْد | All praise |
| لِلَّه | For Allah |
| رَبّ | Lord / Sustainer |
| الْعَالَمِين | All the worlds |

---

### الرَّحْمَنِ الرَّحِيمِ
*Ar-raḥmāni r-raḥīm*
The Most Gracious, the Most Merciful

---

### مَالِكِ يَوْمِ الدِّين
*Māliki yawmi d-dīn*

| Word | Meaning |
|------|---------|
| مَالِك | Master / Owner |
| يَوْم | Day |
| الدِّين | Judgment / Religion |

---

### إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِين
*Iyyāka naʿbudu wa-iyyāka nastaʿīn*

**You alone we worship, and You alone we ask for help**

---

### اهْدِنَا الصِّرَاطَ الْمُسْتَقِيم
*Ihdinā ṣ-ṣirāṭa l-mustaqīm*
**Guide us to the straight path**

---

### صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِم
*Ṣirāṭa lladhīna anʿamta ʿalayhim*
**The path of those You have blessed**

---

### غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّين
*Ghayri l-maghḍūbi ʿalayhim wa-lā ḍ-ḍāllīn*
**Not of those who earned anger, nor of those who went astray**

---

> 🤲 Now when you recite Al-Fatiha in prayer, you understand every word. That connection is priceless.""",
            },
        ],
    },
]

EXTRA_VOCAB = [
    {"arabic": "نَجْمَة",  "english": "Star",      "emoji": "⭐", "phonetic": "najma",
     "letters": ["ن","ج","م","ة"], "context_forms": ["نـ","ـجـ","ـمـ","ـة"], "missing_index": 1, "wrong_choices": ["ب","ك"]},
    {"arabic": "قَمَر",   "english": "Moon",      "emoji": "🌙", "phonetic": "qamar",
     "letters": ["ق","م","ر"], "context_forms": ["قـ","ـمـ","ـر"], "missing_index": 0, "wrong_choices": ["ب","ت"]},
    {"arabic": "بَحْر",   "english": "Sea",       "emoji": "🌊", "phonetic": "baḥr",
     "letters": ["ب","ح","ر"], "context_forms": ["بـ","ـحـ","ـر"], "missing_index": 1, "wrong_choices": ["ك","م"]},
    {"arabic": "جَبَل",   "english": "Mountain",  "emoji": "⛰️", "phonetic": "jabal",
     "letters": ["ج","ب","ل"], "context_forms": ["جـ","ـبـ","ـل"], "missing_index": 2, "wrong_choices": ["ن","ر"]},
    {"arabic": "نَهْر",   "english": "River",     "emoji": "🏞️", "phonetic": "nahr",
     "letters": ["ن","ه","ر"], "context_forms": ["نـ","ـهـ","ـر"], "missing_index": 1, "wrong_choices": ["ب","م"]},
    {"arabic": "يَد",    "english": "Hand",      "emoji": "✋", "phonetic": "yad",
     "letters": ["ي","د"], "context_forms": ["يـ","ـد"], "missing_index": 0, "wrong_choices": ["ب","ك"]},
    {"arabic": "عَيْن",  "english": "Eye",       "emoji": "👁️", "phonetic": "ʿayn",
     "letters": ["ع","ي","ن"], "context_forms": ["عـ","ـيـ","ـن"], "missing_index": 1, "wrong_choices": ["ب","ر"]},
    {"arabic": "أُذُن",  "english": "Ear",       "emoji": "👂", "phonetic": "udhun",
     "letters": ["أ","ذ","ن"], "context_forms": ["أـ","ـذـ","ـن"], "missing_index": 2, "wrong_choices": ["م","ب"]},
    {"arabic": "قَلْب",  "english": "Heart",     "emoji": "❤️", "phonetic": "qalb",
     "letters": ["ق","ل","ب"], "context_forms": ["قـ","ـلـ","ـب"], "missing_index": 1, "wrong_choices": ["ن","م"]},
    {"arabic": "شَجَرَة","english": "Tree",      "emoji": "🌳", "phonetic": "shajara",
     "letters": ["ش","ج","ر","ة"], "context_forms": ["شـ","ـجـ","ـرـ","ـة"], "missing_index": 1, "wrong_choices": ["ب","ك"]},
    {"arabic": "زَهْرَة","english": "Flower",    "emoji": "🌸", "phonetic": "zahra",
     "letters": ["ز","ه","ر","ة"], "context_forms": ["زـ","ـهـ","ـرـ","ـة"], "missing_index": 0, "wrong_choices": ["ب","ن"]},
    {"arabic": "سَمَاء", "english": "Sky",       "emoji": "🌤️", "phonetic": "samāʾ",
     "letters": ["س","م","ا","ء"], "context_forms": ["سـ","ـمـ","ـا","ء"], "missing_index": 1, "wrong_choices": ["ب","ك"]},
]


class Command(BaseCommand):
    help = "Seed demo courses, lessons, and enrol the demo student with progress"

    def handle(self, *args, **options):
        from accounts.models import User, StudentProfile, TeacherProfile
        from curriculum.models import (
            Category, Course, Enrollment, Lesson, LessonProgress, Level
        )
        from games.models import VocabWord

        # ── 1. Get A1 level ──────────────────────────────────────────────
        try:
            a1 = Level.objects.get(code="A1")
        except Level.DoesNotExist:
            self.stdout.write(self.style.ERROR("A1 level not found. Run migrations first."))
            return

        # ── 2. Create demo teacher ───────────────────────────────────────
        teacher_user, created = User.objects.get_or_create(
            email="teacher@learnarabicasl.com",
            defaults={
                "first_name": "Amira",
                "last_name":  "Hassan",
                "role":       User.Role.TEACHER,
            }
        )
        if created:
            teacher_user.set_password("TeacherPass1!")
            teacher_user.save()

        teacher_profile, _ = TeacherProfile.objects.get_or_create(
            user=teacher_user,
            defaults={
                "bio":                "MSc in Arabic Linguistics. 10 years teaching Modern Standard Arabic online.",
                "specialization":     "Modern Standard Arabic & Quranic Arabic",
                "years_of_experience": 10,
                "is_approved":        True,
            }
        )

        # ── 3. Create category ───────────────────────────────────────────
        category, _ = Category.objects.get_or_create(
            slug="arabic-language",
            defaults={"name": "Arabic Language", "is_active": True}
        )

        # ── 4. Create courses + lessons ──────────────────────────────────
        created_courses = []
        for cd in COURSES:
            course, _ = Course.objects.get_or_create(
                slug=cd["slug"],
                defaults={
                    "title":       cd["title"],
                    "description": cd["description"],
                    "level":       a1,
                    "category":    category,
                    "teacher":     teacher_user,
                    "track":       "all",
                    "is_published": True,
                }
            )
            created_courses.append(course)

            for ld in cd["lessons"]:
                Lesson.objects.get_or_create(
                    course=course,
                    slug=ld["slug"],
                    defaults={
                        "order":            ld["order"],
                        "title":            ld["title"],
                        "body_markdown":    ld["body_markdown"],
                        "duration_minutes": ld.get("duration_minutes"),
                        "is_free_preview":  ld["order"] == 1,
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"✓ Created {len(created_courses)} courses"))

        # ── 5. Enrol demo student + mark progress ────────────────────────
        try:
            demo_user    = User.objects.get(email="demo@learnarabicasl.com")
            demo_student = demo_user.student_profile
        except (User.DoesNotExist, StudentProfile.DoesNotExist):
            self.stdout.write(self.style.WARNING("Demo student not found — run create_demo first"))
            return

        for i, course in enumerate(created_courses):
            enrollment, _ = Enrollment.objects.get_or_create(
                student=demo_student,
                course=course,
                defaults={"status": Enrollment.Status.ACTIVE}
            )

            lessons = list(course.lessons.order_by("order"))
            # Course 1: 3 lessons done, Course 2: 2 done, Course 3: 1 done
            lessons_to_complete = [3, 2, 1][i] if i < 3 else 1

            for j, lesson in enumerate(lessons):
                if j < lessons_to_complete:
                    LessonProgress.objects.get_or_create(
                        enrollment=enrollment,
                        lesson=lesson,
                        defaults={"status": LessonProgress.Status.COMPLETED}
                    )
                elif j == lessons_to_complete:
                    LessonProgress.objects.get_or_create(
                        enrollment=enrollment,
                        lesson=lesson,
                        defaults={"status": LessonProgress.Status.IN_PROGRESS}
                    )

        self.stdout.write(self.style.SUCCESS("✓ Demo student enrolled with progress"))

        # ── 6. Add extra vocabulary ──────────────────────────────────────
        added = 0
        for w in EXTRA_VOCAB:
            _, created = VocabWord.objects.get_or_create(
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
                }
            )
            if created:
                added += 1

        self.stdout.write(self.style.SUCCESS(f"✓ Added {added} extra vocab words"))
        self.stdout.write(self.style.SUCCESS("🎉 Demo content seeded successfully!"))

-- =============================================================================
-- Bayt al-Hikma — Flashcard Seed Data
-- Database: MySQL (utf8mb4)
-- Run with: mysql -u <user> -p <dbname> < seed_flashcards.sql
--
-- This script is IDEMPOTENT — it uses INSERT IGNORE so re-running it
-- never creates duplicate decks or cards.
--
-- HOW IT WORKS
-- ~~~~~~~~~~~~
-- The script picks the first 5 published lessons (ordered by level → course →
-- lesson order) and attaches one deck to each.  If your database has fewer
-- than 5 published lessons the extra decks are attached to the last available
-- lesson.
-- =============================================================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- ---------------------------------------------------------------------------
-- 1. Capture lesson IDs into user-defined variables
-- ---------------------------------------------------------------------------

-- Helper view so we can ORDER BY level and re-use the sorted list easily.
-- We use a subquery inline below instead to keep the script dependency-free.

SET @l1 = (
    SELECT l.id
    FROM   curriculum_lesson l
    JOIN   curriculum_course c  ON c.id = l.course_id
    JOIN   curriculum_level  lv ON lv.id = c.level_id
    WHERE  c.is_published = 1
    ORDER  BY lv.`order`, c.id, l.`order`
    LIMIT  1 OFFSET 0
);

SET @l2 = (
    SELECT l.id
    FROM   curriculum_lesson l
    JOIN   curriculum_course c  ON c.id = l.course_id
    JOIN   curriculum_level  lv ON lv.id = c.level_id
    WHERE  c.is_published = 1
    ORDER  BY lv.`order`, c.id, l.`order`
    LIMIT  1 OFFSET 1
);

SET @l3 = (
    SELECT l.id
    FROM   curriculum_lesson l
    JOIN   curriculum_course c  ON c.id = l.course_id
    JOIN   curriculum_level  lv ON lv.id = c.level_id
    WHERE  c.is_published = 1
    ORDER  BY lv.`order`, c.id, l.`order`
    LIMIT  1 OFFSET 2
);

SET @l4 = (
    SELECT l.id
    FROM   curriculum_lesson l
    JOIN   curriculum_course c  ON c.id = l.course_id
    JOIN   curriculum_level  lv ON lv.id = c.level_id
    WHERE  c.is_published = 1
    ORDER  BY lv.`order`, c.id, l.`order`
    LIMIT  1 OFFSET 3
);

SET @l5 = (
    SELECT l.id
    FROM   curriculum_lesson l
    JOIN   curriculum_course c  ON c.id = l.course_id
    JOIN   curriculum_level  lv ON lv.id = c.level_id
    WHERE  c.is_published = 1
    ORDER  BY lv.`order`, c.id, l.`order`
    LIMIT  1 OFFSET 4
);

-- Fall back to @l1 for any slot where not enough lessons exist.
SET @l2 = IFNULL(@l2, @l1);
SET @l3 = IFNULL(@l3, @l1);
SET @l4 = IFNULL(@l4, @l1);
SET @l5 = IFNULL(@l5, @l1);

-- ---------------------------------------------------------------------------
-- 2. Create FlashcardDecks
--    Columns: lesson_id, title, description, is_published, created_at, updated_at
-- ---------------------------------------------------------------------------

INSERT IGNORE INTO flashcards_flashcarddeck
    (lesson_id, title, description, is_published, created_at, updated_at)
VALUES
    (@l1, 'Greetings & Expressions',
     'Essential phrases for everyday Arabic conversations — how to say hello, goodbye, and polite expressions.',
     1, NOW(), NOW()),

    (@l2, 'Numbers 0–20',
     'Cardinal numbers from zero to twenty. Master these to count, give your phone number, and tell the time.',
     1, NOW(), NOW()),

    (@l3, 'Colours',
     'Arabic colour adjectives. Note: adjectives agree in gender with the noun they describe.',
     1, NOW(), NOW()),

    (@l4, 'Family Members',
     'Vocabulary for family relationships. Arabic distinguishes maternal vs paternal relatives — pay attention!',
     1, NOW(), NOW()),

    (@l5, 'Days of the Week & Months',
     'All seven days and twelve Gregorian months in Modern Standard Arabic.',
     1, NOW(), NOW());

-- ---------------------------------------------------------------------------
-- 3. Capture the deck IDs we just created (or that already existed)
-- ---------------------------------------------------------------------------

SET @d_greet   = (SELECT id FROM flashcards_flashcarddeck WHERE title = 'Greetings & Expressions'   LIMIT 1);
SET @d_numbers = (SELECT id FROM flashcards_flashcarddeck WHERE title = 'Numbers 0–20'               LIMIT 1);
SET @d_colours = (SELECT id FROM flashcards_flashcarddeck WHERE title = 'Colours'                    LIMIT 1);
SET @d_family  = (SELECT id FROM flashcards_flashcarddeck WHERE title = 'Family Members'             LIMIT 1);
SET @d_days    = (SELECT id FROM flashcards_flashcarddeck WHERE title = 'Days of the Week & Months'  LIMIT 1);

-- ---------------------------------------------------------------------------
-- 4. Insert Flashcards
--    Columns: deck_id, `order`, front, back, front_lang, back_lang, audio, notes
-- ---------------------------------------------------------------------------

-- ── GREETINGS & EXPRESSIONS (20 cards) ──────────────────────────────────────
INSERT IGNORE INTO flashcards_flashcard
    (deck_id, `order`, front, back, front_lang, back_lang, audio, notes)
VALUES
    (@d_greet,  1, 'مرحباً',            'Hello',                        'ar', 'en', NULL, 'Standard greeting, used any time of day.'),
    (@d_greet,  2, 'السلام عليكم',      'Peace be upon you',            'ar', 'en', NULL, 'Traditional Islamic greeting.'),
    (@d_greet,  3, 'وعليكم السلام',     'And upon you peace',           'ar', 'en', NULL, 'Reply to السلام عليكم.'),
    (@d_greet,  4, 'صباح الخير',        'Good morning',                 'ar', 'en', NULL, ''),
    (@d_greet,  5, 'صباح النور',        'Good morning (reply)',          'ar', 'en', NULL, 'Literally "morning of light".'),
    (@d_greet,  6, 'مساء الخير',        'Good evening',                 'ar', 'en', NULL, ''),
    (@d_greet,  7, 'مساء النور',        'Good evening (reply)',          'ar', 'en', NULL, ''),
    (@d_greet,  8, 'كيف حالك؟',         'How are you?',                 'ar', 'en', NULL, ''),
    (@d_greet,  9, 'بخير، شكراً',       'Fine, thank you',              'ar', 'en', NULL, ''),
    (@d_greet, 10, 'تشرفنا',            'Nice to meet you',             'ar', 'en', NULL, 'Literally "we are honoured".'),
    (@d_greet, 11, 'ما اسمك؟',          'What is your name?',           'ar', 'en', NULL, ''),
    (@d_greet, 12, 'اسمي …',            'My name is …',                 'ar', 'en', NULL, 'Fill in with your name.'),
    (@d_greet, 13, 'من أين أنت؟',       'Where are you from?',          'ar', 'en', NULL, ''),
    (@d_greet, 14, 'أنا من …',          'I am from …',                  'ar', 'en', NULL, ''),
    (@d_greet, 15, 'شكراً',             'Thank you',                    'ar', 'en', NULL, ''),
    (@d_greet, 16, 'عفواً',             'You\'re welcome / Excuse me',  'ar', 'en', NULL, 'Context-dependent.'),
    (@d_greet, 17, 'من فضلك',           'Please',                       'ar', 'en', NULL, ''),
    (@d_greet, 18, 'آسف',               'Sorry',                        'ar', 'en', NULL, ''),
    (@d_greet, 19, 'مع السلامة',        'Goodbye',                      'ar', 'en', NULL, 'Literally "go in safety".'),
    (@d_greet, 20, 'إلى اللقاء',        'See you later',                'ar', 'en', NULL, '');

-- ── NUMBERS 0–20 (21 cards) ─────────────────────────────────────────────────
INSERT IGNORE INTO flashcards_flashcard
    (deck_id, `order`, front, back, front_lang, back_lang, audio, notes)
VALUES
    (@d_numbers,  1, 'صفر',         'Zero',      'ar', 'en', NULL, ''),
    (@d_numbers,  2, 'واحد',        'One',       'ar', 'en', NULL, ''),
    (@d_numbers,  3, 'اثنان',       'Two',       'ar', 'en', NULL, 'Formal; colloquial often "اتنين".'),
    (@d_numbers,  4, 'ثلاثة',       'Three',     'ar', 'en', NULL, ''),
    (@d_numbers,  5, 'أربعة',       'Four',      'ar', 'en', NULL, ''),
    (@d_numbers,  6, 'خمسة',        'Five',      'ar', 'en', NULL, ''),
    (@d_numbers,  7, 'ستة',         'Six',       'ar', 'en', NULL, ''),
    (@d_numbers,  8, 'سبعة',        'Seven',     'ar', 'en', NULL, ''),
    (@d_numbers,  9, 'ثمانية',      'Eight',     'ar', 'en', NULL, ''),
    (@d_numbers, 10, 'تسعة',        'Nine',      'ar', 'en', NULL, ''),
    (@d_numbers, 11, 'عشرة',        'Ten',       'ar', 'en', NULL, ''),
    (@d_numbers, 12, 'أحد عشر',     'Eleven',    'ar', 'en', NULL, ''),
    (@d_numbers, 13, 'اثنا عشر',    'Twelve',    'ar', 'en', NULL, ''),
    (@d_numbers, 14, 'ثلاثة عشر',   'Thirteen',  'ar', 'en', NULL, ''),
    (@d_numbers, 15, 'أربعة عشر',   'Fourteen',  'ar', 'en', NULL, ''),
    (@d_numbers, 16, 'خمسة عشر',    'Fifteen',   'ar', 'en', NULL, ''),
    (@d_numbers, 17, 'ستة عشر',     'Sixteen',   'ar', 'en', NULL, ''),
    (@d_numbers, 18, 'سبعة عشر',    'Seventeen', 'ar', 'en', NULL, ''),
    (@d_numbers, 19, 'ثمانية عشر',  'Eighteen',  'ar', 'en', NULL, ''),
    (@d_numbers, 20, 'تسعة عشر',    'Nineteen',  'ar', 'en', NULL, ''),
    (@d_numbers, 21, 'عشرون',       'Twenty',    'ar', 'en', NULL, '');

-- ── COLOURS (13 cards) ──────────────────────────────────────────────────────
INSERT IGNORE INTO flashcards_flashcard
    (deck_id, `order`, front, back, front_lang, back_lang, audio, notes)
VALUES
    (@d_colours,  1, 'أحمر',      'Red',           'ar', 'en', NULL, ''),
    (@d_colours,  2, 'أزرق',      'Blue',          'ar', 'en', NULL, ''),
    (@d_colours,  3, 'أخضر',      'Green',         'ar', 'en', NULL, ''),
    (@d_colours,  4, 'أصفر',      'Yellow',        'ar', 'en', NULL, ''),
    (@d_colours,  5, 'أبيض',      'White',         'ar', 'en', NULL, ''),
    (@d_colours,  6, 'أسود',      'Black',         'ar', 'en', NULL, ''),
    (@d_colours,  7, 'برتقالي',   'Orange',        'ar', 'en', NULL, 'From the word برتقال (orange fruit).'),
    (@d_colours,  8, 'بنفسجي',    'Purple / Violet','ar', 'en', NULL, 'From بنفسج, violet flower.'),
    (@d_colours,  9, 'وردي',      'Pink',          'ar', 'en', NULL, 'From وردة, rose.'),
    (@d_colours, 10, 'بني',       'Brown',         'ar', 'en', NULL, ''),
    (@d_colours, 11, 'رمادي',     'Grey',          'ar', 'en', NULL, 'From رماد, ash.'),
    (@d_colours, 12, 'ذهبي',      'Golden',        'ar', 'en', NULL, 'From ذهب, gold.'),
    (@d_colours, 13, 'فضي',       'Silver',        'ar', 'en', NULL, 'From فضة, silver.');

-- ── FAMILY MEMBERS (15 cards) ───────────────────────────────────────────────
INSERT IGNORE INTO flashcards_flashcard
    (deck_id, `order`, front, back, front_lang, back_lang, audio, notes)
VALUES
    (@d_family,  1, 'أب',       'Father',                 'ar', 'en', NULL, ''),
    (@d_family,  2, 'أم',       'Mother',                 'ar', 'en', NULL, ''),
    (@d_family,  3, 'أخ',       'Brother',                'ar', 'en', NULL, ''),
    (@d_family,  4, 'أخت',      'Sister',                 'ar', 'en', NULL, ''),
    (@d_family,  5, 'ابن',      'Son',                    'ar', 'en', NULL, ''),
    (@d_family,  6, 'ابنة',     'Daughter',               'ar', 'en', NULL, 'Also بنت in colloquial speech.'),
    (@d_family,  7, 'جد',       'Grandfather',            'ar', 'en', NULL, ''),
    (@d_family,  8, 'جدة',      'Grandmother',            'ar', 'en', NULL, ''),
    (@d_family,  9, 'عم',       'Paternal uncle',         'ar', 'en', NULL, "Father's brother."),
    (@d_family, 10, 'خال',      'Maternal uncle',         'ar', 'en', NULL, "Mother's brother."),
    (@d_family, 11, 'عمة',      'Paternal aunt',          'ar', 'en', NULL, "Father's sister."),
    (@d_family, 12, 'خالة',     'Maternal aunt',          'ar', 'en', NULL, "Mother's sister."),
    (@d_family, 13, 'ابن عم',   'Cousin (paternal male)', 'ar', 'en', NULL, ''),
    (@d_family, 14, 'زوج',      'Husband',                'ar', 'en', NULL, ''),
    (@d_family, 15, 'زوجة',     'Wife',                   'ar', 'en', NULL, '');

-- ── DAYS OF THE WEEK & MONTHS (19 cards) ────────────────────────────────────
INSERT IGNORE INTO flashcards_flashcard
    (deck_id, `order`, front, back, front_lang, back_lang, audio, notes)
VALUES
    (@d_days,  1, 'الأحد',      'Sunday',    'ar', 'en', NULL, 'First day of the week in many Arab countries.'),
    (@d_days,  2, 'الاثنين',    'Monday',    'ar', 'en', NULL, ''),
    (@d_days,  3, 'الثلاثاء',   'Tuesday',   'ar', 'en', NULL, ''),
    (@d_days,  4, 'الأربعاء',   'Wednesday', 'ar', 'en', NULL, ''),
    (@d_days,  5, 'الخميس',     'Thursday',  'ar', 'en', NULL, ''),
    (@d_days,  6, 'الجمعة',     'Friday',    'ar', 'en', NULL, 'The holy day of congregational prayer.'),
    (@d_days,  7, 'السبت',      'Saturday',  'ar', 'en', NULL, ''),
    (@d_days,  8, 'يناير',      'January',   'ar', 'en', NULL, ''),
    (@d_days,  9, 'فبراير',     'February',  'ar', 'en', NULL, ''),
    (@d_days, 10, 'مارس',       'March',     'ar', 'en', NULL, ''),
    (@d_days, 11, 'أبريل',      'April',     'ar', 'en', NULL, ''),
    (@d_days, 12, 'مايو',       'May',       'ar', 'en', NULL, ''),
    (@d_days, 13, 'يونيو',      'June',      'ar', 'en', NULL, ''),
    (@d_days, 14, 'يوليو',      'July',      'ar', 'en', NULL, ''),
    (@d_days, 15, 'أغسطس',      'August',    'ar', 'en', NULL, ''),
    (@d_days, 16, 'سبتمبر',     'September', 'ar', 'en', NULL, ''),
    (@d_days, 17, 'أكتوبر',     'October',   'ar', 'en', NULL, ''),
    (@d_days, 18, 'نوفمبر',     'November',  'ar', 'en', NULL, ''),
    (@d_days, 19, 'ديسمبر',     'December',  'ar', 'en', NULL, '');

-- =============================================================================
-- Done. Verify with:
--   SELECT d.title, COUNT(c.id) AS cards
--   FROM   flashcards_flashcarddeck d
--   LEFT JOIN flashcards_flashcard c ON c.deck_id = d.id
--   GROUP BY d.id, d.title;
-- =============================================================================

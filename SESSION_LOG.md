# Bayt al-Hikma — Session Log

A running record of work sessions. Append new sessions at the top.

---

## Session 6 · 2026-05-16

**Coverage:** Phase 9 — Games & Flashcards (seed data).
**Status at end:** Flashcards app was already fully built (models, views, games, templates, teacher deck builder — all wired up). This session added the missing seed data via a management command so there are real Arabic cards to study out of the box.

### What was built — file by file

| File | Status | Purpose |
|------|--------|---------|
| `flashcards/management/__init__.py` | created | Python package marker |
| `flashcards/management/commands/__init__.py` | created | Python package marker |
| `flashcards/management/commands/seed_flashcards.py` | created | Management command that creates 5 Arabic vocabulary decks (83 cards total). Idempotent — safe to run multiple times. |

### Seed decks created

| Deck | Cards | Content |
|------|-------|---------|
| Greetings & Expressions | 20 | مرحباً, السلام عليكم, كيف حالك؟, etc. |
| Numbers 0–20 | 21 | صفر through عشرون |
| Colours | 13 | أحمر, أزرق, أخضر, etc. |
| Family Members | 15 | أب, أم, أخ, أخت, جد, زوج, etc. |
| Days of the Week & Months | 19 | Days + all 12 Gregorian months |

### How to run

```bash
python manage.py seed_flashcards
```

Decks attach to the first published lessons (ordered by level → course → lesson order). Running again is safe — existing decks and cards are skipped or updated, never duplicated.

### What was already in place (no changes needed)

The flashcards app was built in a prior session and was complete:
- `FlashcardDeck`, `Flashcard`, `FlashcardReview` models + migration
- Student study modes: flip-card session, match game, translation sprint
- `mark_review()` service — streak/mastery tracking (3 correct in a row = mastered)
- Teacher deck builder views + forms (create/edit/delete decks and cards)
- All templates: `deck_intro`, `study`, `deck_summary`, `match`, `sprint`, `teach/deck_form`, `teach/deck_manage`, `teach/card_form`
- `lesson_detail.html` already surfaces linked decks with a "Study cards" button
- `course_manage.html` already links to deck management per lesson
- URLs mounted in `core/urls.py`

### Decisions locked

- **Seed as a management command, not a data migration.** Vocabulary content can evolve; a migration bakes it into the schema history forever. A command is idempotent, easy to re-run, and easy to extend.
- **5 decks cover A1/A2 core vocabulary.** Greetings, numbers, colours, family, and calendar are the universal first-lesson staples. Teachers add topic-specific decks via the UI.
- **3-correct-streak for mastery.** Simple heuristic, no full SM-2 complexity. `next_due_at` can be added later if spaced repetition is desired.
- **Match game capped at 8 cards (16 tiles).** Fits a 4×4 grid without scrolling; random subset chosen per play for replay value.
- **Sprint needs ≥ 4 cards.** Guard in `sprint_game` redirects back with a warning message if the deck is too small.

### Where to pick up — Phase 8 (Billing) OR end-to-end testing

**Option 1 — End-to-end testing (recommended first)**
Walk through the full student journey: signup → placement → catalogue → enrol → lesson (with flashcard decks) → match game → sprint → quiz pass → certificate. Also test teacher deck builder workflow.

**Option 2 — Phase 8: Billing**
New `billing` app:
- `Plan` (Free, Individual, Family, Institution) — name, monthly_price, features JSON
- `Subscription` (FK student/parent + plan, status, started_at, current_period_end, cancel_at_period_end)
- `PaymentEvent` (Stripe-style audit log: invoice id, amount, status, raw_payload)
- Free plan is the default for new students; paywall gates premium courses (new `Course.requires_subscription` boolean)
- Household plan: one parent's subscription covers their linked children
- Stripe wiring (test-mode keys in `.env`) optional — can stub with admin "mark paid" actions for MVP

### Future phases

| Phase | Scope |
|-------|-------|
| 8 | Billing — Subscription, Plan, PaymentEvent, household plans |
| 10+ | Notifications · Mobile-friendly tuning · i18n (Arabic UI) · Discussion forums · Live Zoom integration · Analytics dashboard |

---

## Session 5 · 2026-05-05

**Coverage:** Phase 7 — placement test, plus follow-on cleanup of the assessments seed.
**Status at end:** Phase 7 complete. Placement quiz writes `StudentProfile.current_level` based on score bands; result page shows assigned level + recommended courses; dashboard CTA links to it for unplaced students. MVP is functionally complete (signup → placement → catalogue → enrol → learn → assess → certificate).

### What was built — file by file

| File | Status | Purpose |
|------|--------|---------|
| `assessments/services.py` | extended | `PLACEMENT_BANDS` constant (95→C2, 85→C1, 70→B2, 50→B1, 30→A2, 0→A1); `_level_code_for_score(score)`; `_apply_placement_effect(submission)`; `apply_pass_effects` placement branch runs unconditionally (no pass/fail guard) |
| `assessments/views.py` | extended | `submission_result` enriched with `recommended_courses` for placement; `_recommend_for_placement(submission)` filters by track + level (own + next + open) and excludes already-enrolled, sorted by relevance; `_finalize_submission` placement-specific flash message reports the assigned level |
| `templates/assessments/submission_result.html` | extended | Three score-block variants: placement (level + recommendations grid), graded pass/fail badge, awaiting-grade alert |
| `dashboards/views.py` | extended | `StudentDashboardView` fetches `placement_quiz` (most-recent published) and exposes it in context |
| `templates/dashboards/student.html` | extended | No-level CTA wired to `placement_quiz.id`; falls back to disabled "unavailable" button if no published placement quiz exists |

No new tables, no migrations — Phase 7 is pure logic + template changes layered on top of the existing assessments app.

### Decisions locked

- **Score bands as code constants, not DB rows.** Mapping changes rarely; greppable in source. Edit `PLACEMENT_BANDS` to retune.
- **C2 capped behind 95% threshold; C2 not awarded by default.** Sustained mastery shouldn't be granted by one quiz. Conservative default — operators can adjust by editing the constant.
- **Placement always writes a level**, even on a "failing" submission, because a low score still places the student at A1 (the floor). The pass/fail framing is bypassed.
- **Re-takes overwrite `current_level`.** No history preservation on the cached level — but the Submission row remains in the audit trail. Idempotency guard skips the write if the same level would be re-set.
- **Recommendations: same-level OR next-level OR open**, age-track-matched, exclude already-enrolled, sorted by relevance (same-level first). Up to 6 cards.
- **Placement quizzes should be auto-gradable only.** A short_answer question blocks the placement effect until a teacher grades it manually — defeats the purpose of placement-as-onboarding. Recommended pattern: build placement tests with mcq/multi/tf only.

### Key technical notes

- **`apply_pass_effects` placement branch runs *before* the pass guard.** Other quiz kinds early-return on `not submission.passed`; placement does not.
- **`_recommend_for_placement` uses `Case/When` annotation** for relevance ordering (same-level=0, next-level=1, open=2). Keeps the sort in SQL, no Python post-processing.
- **Multiple placement quizzes are non-buggy but messy.** Dashboard picks "most recent published"; whichever a student takes will still write a level via the placement effect. Cleanup pattern: unpublish or delete the older.
- **Stale code path footgun.** A submission graded *before* `apply_pass_effects` learned the placement branch won't have written a level. Fix: admin "Re-run the auto-grader" action, or re-take.
- **MySQL subquery `=` vs `IN`.** `WHERE x = (SELECT id FROM...)` errors with "Subquery returns more than 1 row" the moment two placements coexist. `IN (...)` is the safe form for cleanup queries that may target multiple rows.
- **Template typo nuance reminder:** `{# … #}` is single-line only. `{% comment %} … {% endcomment %}` for blocks. (Already burned this twice this project.)

### Verifications passed

- `python manage.py check` — 0 issues.
- New student signs up → dashboard shows yellow CTA with **Take placement test** linked to `/quizzes/<id>/`.
- Placement quiz auto-grades MCQ + multi-select + true/false; submitting flips status to GRADED, fires placement effect.
- 71% submission mapped to B2 (score band `70 → B2`) and wrote `StudentProfile.current_level_id`.
- Result page renders the level callout + 6 recommended course cards, sorted same-level → next-level → open.
- Dashboard CTA disappears once `current_level` is set; stat card shows the CEFR code.
- Catalogue eligibility respects the new level — B1 and B2 courses now enrol-able by the placed student; C1 still blocked.
- Re-take overwrites cleanly; idempotent on no-change.

### Where to pick up — Phase 8 (Billing) — OR continue MVP testing

MVP is functionally complete. Sensible options for the next session:

**Option 1 — User-test the platform end-to-end** before adding more code. Walk through:
- Cold-visitor signup as student, parent, kid
- Placement, enrol, lesson watch (video + text), quiz pass, lesson done
- Course final, certificate generation, certificate page printable
- Teacher view of own courses + recent activity
- Parent linked-children view

**Option 2 — Phase 8: Billing.** New `billing` app with:
- `Plan` (Free, Individual, Family, Institution) — name, monthly_price, features JSON
- `Subscription` (FK student/parent + plan, status, started_at, current_period_end, cancel_at_period_end)
- `PaymentEvent` (stripe-style audit log: invoice id, amount, status, raw_payload)
- Free plan is the default for new students; paywall gates premium courses (new `Course.requires_subscription` boolean)
- Household plan: one parent's subscription covers their linked children
- Stripe wiring (test mode keys in `.env`) optional — can stub with admin "mark paid" actions for MVP

**Option 3 — Phase 9: Games & Flashcards.** Sub-table `Game` with config JSON, render with small JS modules per game type. Flashcard deck for vocabulary lessons. More fun than billing if motivation matters.

### Future phases

| Phase | Scope |
|-------|-------|
| 10+ | Notifications · Mobile-friendly tuning · i18n (Arabic UI) · Discussion forums · Live Zoom integration · Analytics dashboard |

---

## Session 4 · 2026-05-04

**Coverage:** Phase 6 — assessments app (6A → 6D), plus a self-hosted-video sidequest and a comprehensive seed.
**Status at end:** Phase 6 complete. Quizzes auto-grade, lesson/course completion propagates from quiz passes, certificates mint and serve at `/certificates/<code>/`. Self-hosted MP4 videos play inline. Phase 7 (placement test) next.

### What was built — file by file

| File | Status | Purpose |
|------|--------|---------|
| `assessments/` app | scaffolded | `__init__.py`, `apps.py`, `migrations/__init__.py` |
| `assessments/models.py` | written | `Quiz` (3 kinds: lesson_quiz / course_final / placement), `Question` (4 kinds: mcq / multi_select / true_false / short_answer), `Choice`, `Submission` (3 statuses), `Answer` |
| `assessments/migrations/0001_initial.py` | generated | 5 tables + 3 unique constraints |
| `assessments/admin.py` | written | 5 ModelAdmins + 3 inlines (`QuestionInline` on Quiz, `ChoiceInline` on Question, read-only `AnswerInline` on Submission) + "Re-grade selected" admin action |
| `assessments/views.py` | written | `quiz_intro`, `start_quiz` (POST), `take_question` (GET+POST wizard), `submit_quiz`, `submission_result`; private `_finalize_submission` helper to share the submit-and-grade path |
| `assessments/urls.py` | created | 5 routes; mounted at root in `core/urls.py` |
| `assessments/services.py` | written | `grade_answer` (per-question), `grade_submission` (whole-submission, idempotent, runs `apply_pass_effects` once status flips to GRADED), `apply_pass_effects` (lesson-quiz → LessonProgress.completed; course-final → Enrollment.completed + certificate code) |
| `templates/assessments/quiz_intro.html` | created | Quiz landing page: question count, threshold, time limit, past attempts, Start/Resume button |
| `templates/assessments/take_question.html` | created | One-question-per-page wizard; per-kind inputs (radio/checkbox/textarea); progress bar; question-list sidebar with jumps |
| `templates/assessments/submission_result.html` | created | Score block, pass/fail badge, ✅/❌ on each answer, explanation when graded, Take-again button |
| `curriculum/models.py` | extended | `Enrollment.certificate_code` (32-char hex, db_index, capability-URL token); `Lesson.video_file` FileField for self-hosted MP4 |
| `curriculum/migrations/0003_enrollment_certificate_code.py` | generated | Add `certificate_code` to Enrollment |
| `curriculum/migrations/0004_lesson_video_file.py` | generated | Add `video_file` to Lesson |
| `curriculum/views.py` | extended | `complete_lesson` (POST manual completion), `certificate` (public page); `lesson_detail` extended to fetch `progress`, `completed_lesson_ids`, `lesson_quizzes`, and to look up enrolment even on free-preview lessons; `course_detail` exposes `enrollment` + `course_final` to template |
| `curriculum/urls.py` | extended | `complete_lesson` route added; certificate route mounted top-level in `core/urls.py` for shareable URLs |
| `core/urls.py` | extended | `/certificates/<code>/` route at top level (no auth) |
| `templates/curriculum/lesson_detail.html` | extended | Linked lesson quizzes section ("Check your understanding"); ✅ Completed badge; Mark-as-complete button (manual or quiz path); sidebar checkmarks for completed lessons; HTML5 `<video>` precedence over iframe when `video_file` is set |
| `templates/curriculum/course_detail.html` | extended | Enrollment status branching (active vs completed); certificate link when course finished; Take-final-exam button when enrolled |
| `templates/curriculum/certificate.html` | created | Branded printable certificate page with print CSS; capability-URL access (no login required) |

### Decisions locked

- **Three quiz kinds, one model.** `lesson_quiz` / `course_final` / `placement` differ only in their downstream effects, not in their data shape. `clean()` enforces the right scope per kind.
- **Multi_select grading is set-equality, not partial credit.** Picking the right 2 of 3 + 1 wrong → 0. Strict default; can relax later if pedagogy calls for it.
- **`PROTECT` on `Question` from `Answer` and on `Quiz` from `Submission`.** Never silently lose student answers; teachers must explicitly de-activate, not delete.
- **Re-takes get new Submission rows.** No `unique_together(quiz, student)`. History never overwritten.
- **Score is a percentage (0–100), `passed` is denormalised.** Cross-quiz comparison is meaningful; `passed` indexable for analytics.
- **`grade_submission` triggers `apply_pass_effects` automatically** when status flips to GRADED. Admin re-grade action hits the same path. Idempotent.
- **Capability-URL certificates.** No auth required to view; 32-char hex code (`secrets.token_hex(16)`) is the access key. Status must be `completed` so a leaked code from a partial completion can't render.
- **`certificate_code` lives on Enrollment, not a separate model.** 1:1 with completed enrolment; no need for a new table.
- **Manual "Mark as complete" + quiz-pass auto-complete are both paths.** Quiz path is monotonic; clicking the button on a completed lesson is a no-op. Auto-redirect to next lesson on click for momentum.
- **Free-preview lessons get a completion button too** when the viewer is enrolled (special enrolment lookup added in `lesson_detail`).
- **Self-hosted MP4 takes precedence over external embed URL.** Two coexisting fields on Lesson; template's `{% if lesson.video_file %}` ladder picks file over URL. Backward-compatible with all existing YouTube URLs.

### Key technical notes

- **One-question-per-page = single POST per nav click.** Each "Save & previous" / "Save & next" / "Save & submit" hits the same view; the `action` POST value tells it where to go. Per-question save means jumping via the sidebar never loses an answer. Answer upsert is via `UniqueConstraint(submission, question)` — re-answering re-`set()`s the M2M choices on the existing row.
- **Defensive POST filtering** in `_save_answer`: `question.choices.filter(id__in=ids)` strips any choice IDs not belonging to this question, even if a hand-crafted POST tries to inject them.
- **Empty-answer rows auto-created** by the grader for any question the student skipped; ensures the percentage denominator is right and unanswered questions count as 0.
- **You cannot redirect from one POST to another POST endpoint.** 302 responses become GET on the next request, so chaining `take_question` (POST) → `submit_quiz` (POST via redirect) → 405 Method Not Allowed. Fixed by extracting `_finalize_submission` and calling it inline from take_question's "finish" branch.
- **Console email backend wraps long URLs at column 76 with `=\n`** (quoted-printable). Switched dev to file-based email backend (`sent_emails/`, gitignored) to keep reset URLs unwrapped.
- **YouTube error 153 + ad-blockers + region restrictions** can all break iframe embeds even on supposedly-embeddable videos. Added a parallel self-hosted path (`Lesson.video_file`) so platform doesn't depend on third-party iframe permission.
- **Multi-line `{# … #}` comments don't work in Django templates** — they leak literal text and any embedded HTML tags (`<video>`, `<iframe>`) get parsed by the browser, breaking the page. Caught it twice; from now on always `{% comment %}…{% endcomment %}` for any block comment.
- **`prepopulated_fields` only fires on the admin ADD form**, not edit. Renaming a Course title in admin keeps the original slug, which is what we want — but the corollary is that if you DO want a new slug, you have to clear it manually so `save()`'s `slugify(self.title)` fallback kicks in.

### Verifications passed

- `python manage.py check` — 0 issues after each sub-phase.
- All migrations applied cleanly (assessments 0001, curriculum 0003, curriculum 0004).
- Quiz wizard: start → walk through questions → save & submit → result page renders score, pass/fail, ✅/❌ marks, explanations, Take-again button.
- Lesson-quiz pass propagated `LessonProgress.completed` (badge + sidebar checkmark visible); dashboard progress bar advanced.
- Course-final pass flipped `Enrollment.status='completed'`, minted `certificate_code`, made `View certificate` button appear; certificate page rendered with student name, course title, level, date, verification code, print CSS.
- Manual "Mark as complete" on a quizless lesson updated `LessonProgress` and auto-advanced to next lesson.
- Self-hosted MP4 plays inline via HTML5 `<video>` (9 lessons in "Learn Arabic from scratch — The Speaking Course for Absolute Beginners"). YouTube embed URL coexists as fallback for any lesson without a file.
- Comprehensive seed loaded: 6 categories, 11 courses (10 seeded + 1 video course), 39 lessons + 9 video lessons, 4 lesson quizzes, 2 course finals.

### Where to pick up — Phase 7 (placement test)

Wires up the third Quiz kind. Sub-tasks:

1. Extend `assessments/services.py` `apply_pass_effects` placement branch:
   - Compute `target_level` from score bands (e.g. 0–20% → A1, 20–40% → A2, …, 80–100% → C1).
   - Write `student.current_level = target_level`, `save(update_fields=["current_level"])`.
2. Treat *every* placement submission as "passing" for the side-effect path — the score band, not pass/fail, decides the level. Override `apply_pass_effects`'s "if not submission.passed: return" guard for placement.
3. New result-page variant for placement: instead of pass/fail badge, show "You're at level B1 — here are courses we recommend".
4. Surface a "Take placement test" CTA on the student dashboard for students with no `current_level`, replacing the disabled Phase 7 placeholder button.
5. Decide: only one published placement quiz at a time? Or many (e.g. kids vs adult)? MVP says one; revisit if needed.

### Future phases

| Phase | Scope |
|-------|-------|
| 8 | Billing — Subscription, Plan, PaymentEvent, household plans |
| 9 | Games & Flashcards — `Game.config` JSON, small JS module per game type |

---

## Session 3 · 2026-05-02

**Coverage:** Phase 5 — Bootstrap UI (5A → 5E)
**Status at end:** Phase 5 complete. Public site runs end-to-end: home → catalogue → course detail → enrol → lesson player → progress; signup / login / logout / password reset; role-dispatching dashboard. Phase 6 (assessments) next.

### What was built — file by file

| File | Status | Purpose |
|------|--------|---------|
| `templates/base.html` | created | Site-wide layout: navbar, footer, brand, messages, blocks (`title`, `extra_head`, `content`, `extra_js`) |
| `templates/pages/home.html` | created | Public homepage: hero + 3 feature columns; CTA branches on auth |
| `static/css/site.css` | created | Tiny global overrides + Arabic font stack (`[lang="ar"]`), course-card hover lift |
| `core/context_processors.py` | created | Injects `SITE_NAME` into every template |
| `pages/` app | scaffolded | `__init__.py`, `apps.py`, `views.py` (`HomeView`), `urls.py`, `migrations/__init__.py` |
| `core/settings.py` | extended | `templates/` dir, `static/` dir, context processor, `LOGIN_URL`/redirects, file-based email backend in dev, `pages` + `dashboards` apps |
| `core/urls.py` | extended | mounts `accounts/` (ours), `accounts/` (built-in), `courses/`, `dashboard/`, `pages.urls` (`/`); serves `/media/` in dev |
| `curriculum/views.py` | written | `course_list` (filtered), `course_detail`, `enrol` (POST, login_required, eligibility re-check), `lesson_detail` (free-preview-or-enrolled gate, progress upsert, prev/next pager) |
| `curriculum/urls.py` | created | 4 routes: catalogue, detail, enrol, lesson_detail |
| `templates/curriculum/course_list.html` | created | Sidebar filters (`q`, level, category, track) + responsive course-card grid |
| `templates/curriculum/course_detail.html` | created | Breadcrumb, lesson outline (lock icons for non-enrolled), sticky enrol box with 5-branch logic |
| `templates/curriculum/lesson_detail.html` | created | Lesson sidebar, iframe video, body, attachments by kind, prev/next pager |
| `accounts/forms.py` | created | `SignupForm` (UserCreationForm subclass): role (student/parent only), age_track (conditional), name, email, password validators |
| `accounts/views.py` | written | `SignupView` (CreateView): saves user via signal, applies age_track, auto-logs-in |
| `accounts/urls.py` | created | `/accounts/signup/` |
| `templates/registration/login.html` | created | Bootstrap login (form field is `username` even though model uses email) |
| `templates/registration/logged_out.html` | created | Logout confirmation |
| `templates/registration/signup.html` | created | Signup form with JS-toggled age_track row |
| `templates/registration/password_reset_form.html` | created | Step 1: enter email |
| `templates/registration/password_reset_done.html` | created | Step 2: "check your email" |
| `templates/registration/password_reset_confirm.html` | created | Step 3: set new password (handles `validlink=False`) |
| `templates/registration/password_reset_complete.html` | created | Step 4: success |
| `templates/registration/password_reset_subject.txt` | created | Branded email subject |
| `templates/registration/password_reset_email.html` | created | Branded email body |
| `dashboards/` app | scaffolded | `__init__.py`, `apps.py`, `views.py`, `urls.py`, `migrations/__init__.py` |
| `dashboards/views.py` | written | `dashboard` dispatcher + `StudentDashboardView`, `TeacherDashboardView`, `ParentDashboardView`; admin role redirects to `/admin/`; missing-role 403 |
| `templates/dashboards/student.html` | created | Stat cards, no-level warning, enrolment cards with progress bars |
| `templates/dashboards/teacher.html` | created | Stat cards, course table with active enrolment counts, recent lesson activity feed |
| `templates/dashboards/parent.html` | created | Linked-children cards (level + enrolment count) |
| `templates/dashboards/no_role.html` | created | Defensive 403 page |
| `.gitignore` | extended | added `sent_emails/` |

### Decisions locked

- **Three-layer template lookup:** project-level `templates/` for `base.html` and cross-cutting pages; app-level `templates/<app>/` for app-specific pages; `templates/registration/` is a Django convention for built-in auth views.
- **Bootstrap 5 + Bootstrap Icons via CDN.** No npm, no build step, no JS framework. Utility classes do 95% of the styling; `static/css/site.css` is intentionally tiny (~30 lines).
- **`SITE_NAME` injected via context processor**, so every template (navbar, emails, titles) reads from the same env var. Renaming the brand stays a one-env-edit operation.
- **All catalogue filters via querystring**, never POST. URLs are bookmarkable / shareable; reload preserves filter state with no JS.
- **Eligibility computed in views, displayed in templates.** `services.student_can_enroll` is the single source of truth; templates branch on `eligibility.ok` and render `eligibility.message`.
- **Enrol endpoint is `@require_POST` + `@login_required` + server-side eligibility re-check.** Defence in depth — if the POST somehow bypasses the template's disabled state, the view rolls back the row.
- **Lesson access:** `is_free_preview=True` → public; otherwise must be authenticated student with **active** Enrollment. Cancelled enrolments don't grant access.
- **`LessonProgress` upsert on GET** is the only write-on-GET in the app. Idempotent: re-visit just stamps `last_viewed_at`; never downgrades `completed` to `in_progress`.
- **Single `/dashboard/` URL, role-dispatched.** No `/dashboard/teacher/` URLs to leak privilege; role lookup happens at request time.
- **Admin role → redirect to `/admin/`.** Don't rebuild Django's admin as a custom dashboard.
- **Public signup roles limited to student + parent.** Teachers and admins are created from the Django admin only — no public path to privilege escalation.
- **Email backend in dev:** **file-based**, not console. Console backend QP-wraps long URLs at column 76 with `=\n`, breaking copy-paste of password-reset links. File backend writes raw, unwrapped emails to `sent_emails/` (gitignored).

### Key technical notes

- **`select_related` / `prefetch_related` everywhere there's an FK loop.** Catalogue, course detail, lesson sidebar, dashboards — every N+1 query was killed at the queryset level.
- **`Count` annotations with `filter=Q(...)`** on the teacher dashboard count *only active* enrolments without a separate query.
- **Stat math in Python, not SQL,** for division-by-zero and rounding clarity.
- **Form's `username` field name in `LoginView`** maps to our `email` field via `USERNAME_FIELD`. Django decouples the *form* field name from the *model* field name.
- **Signal still does the heavy lifting.** `SignupForm.save()` calls `user.save()` → `post_save` creates the matching profile → form patches `age_track` with `update_fields=["age_track"]` (single column write).
- **Password-reset token invalidation:** Django hashes `pk + password + last_login` into the token. Logging in (any method) updates `last_login` → invalidates outstanding reset tokens. Diagnostic shell snippet `default_token_generator.make_token(u)` mints a fresh URL bypassing email.
- **JS on signup is purely cosmetic.** Server-side `clean()` enforces "if student, age_track required."
- **`sticky-lg-top` on enrol box and lesson sidebar** keeps the action visible on desktop scroll while still stacking cleanly on mobile.
- **`order-lg-2` flips column order** so the lesson sidebar is right-of-content on desktop but stacks below on mobile.

### Verifications passed

- `python manage.py check` — 0 issues after each sub-phase (5A, 5B, 5C, 5D, 5E).
- Homepage at `/` — renders, navbar shows brand, auth state correct.
- Catalogue at `/courses/` — filters work, querystring round-trips, empty state renders.
- Course detail — breadcrumb, badges, sticky enrol box, lesson outline (locks visible to non-enrolled), 5-branch enrol box.
- Enrol POST → redirect to first lesson; idempotent on double-click; eligibility re-check works (student without `current_level` blocked with `no_level` reason).
- Lesson player — iframe placeholder area, body, attachments by kind, prev/next pager, `LessonProgress` row created with `last_viewed_at` stamped.
- Signup → auto-login → home with navbar avatar dropdown.
- Logout → "Signed out" page → sign back in works.
- Password reset round-trip: form → email file written to `sent_emails/` → click clean URL → set-password form → success page → login with new password works.
- All three role dashboards render with seeded data; admin redirects to `/admin/`.

### Where to pick up — Phase 6 (Assessments)

New models in a new `assessments` app:

1. **Quiz** — `course` FK (or null for placement test), `kind` (`lesson_quiz` / `course_final` / `placement`), `title`, `pass_threshold` (e.g. 70%), `randomize_questions`, `time_limit_minutes`.
2. **Question** — `quiz` FK, `order`, `text`, `kind` (`mcq` / `multi_select` / `true_false` / `short_answer`), `points` (default 1), `explanation` (shown after submission).
3. **Choice** — `question` FK, `order`, `text`, `is_correct`. UniqueConstraint `(question, order)`.
4. **Submission** — `quiz` FK, `student` FK, `started_at`, `submitted_at`, `score`, `passed`. UniqueConstraint `(quiz, student, started_at)` so re-takes are allowed but each attempt is its own row.
5. **Answer** — `submission` FK, `question` FK, optional `selected_choices` (M2M to Choice), `text_answer` (for short-answer), `is_correct`, `points_awarded`.

Then:

- Auto-grade MCQ / multi-select / true-false in `services.grade_submission(submission)`.
- Short-answer questions stay manual (teacher reviews in admin).
- Hook lesson_quiz pass → mark `LessonProgress.status = COMPLETED`.
- Hook course_final pass → set `Enrollment.status = COMPLETED`, set `completed_at`, optionally generate certificate URL.
- Phase 7: placement quiz writes `StudentProfile.current_level` based on score band.

Sub-phase order will be:

- **6A** — assessments app + models + migrations + admin
- **6B** — quiz player UI (one question per page or all at once — to be decided), submission flow
- **6C** — auto-grader + result page + retake button
- **6D** — wire lesson_quiz to LessonProgress, course_final to Enrollment + simple certificate page

### Future phases

| Phase | Scope |
|-------|-------|
| 7 | Placement test as `Quiz.kind = "placement"` writing `current_level` |
| 8 | Billing — Subscription, Plan, PaymentEvent, household plans |
| 9 | Games & Flashcards — `Game.config` JSON, small JS module per game type |

---

## Session 2 · 2026-05-01

**Coverage:** Phase 4 — curriculum app (4A → 4F)
**Status at end:** Phase 4 complete. 11 tables live, levels seeded, admin wired, eligibility helper in place. Phase 5 (Bootstrap UI) next.

### What was built — file by file

| File | Status | Purpose |
|------|--------|---------|
| `curriculum/models.py` | written | `Level`, `Category`, `Course`, `Lesson`, `LessonAttachment`, `Enrollment`, `LessonProgress` |
| `accounts/models.py` | extended | added `StudentProfile.current_level → curriculum.Level` (cached, nullable, SET_NULL) |
| `core/settings.py` | extended | `MEDIA_URL`, `MEDIA_ROOT`, `DEFAULT_AUTO_FIELD = BigAutoField` |
| `core/urls.py` | extended | `/media/` served in dev when `DEBUG=True` |
| `curriculum/migrations/0001_initial.py` | generated | 7 curriculum tables + 4 unique constraints |
| `accounts/migrations/0002_studentprofile_current_level.py` | generated | cross-app FK |
| `curriculum/migrations/0002_seed_levels.py` | written | data migration seeding A1 → C2 (idempotent, reversible) |
| `curriculum/admin.py` | written | 7 ModelAdmins + 2 inlines (`LessonInline` on Course, `LessonAttachmentInline` on Lesson) |
| `curriculum/services.py` | created | `student_can_enroll(student, course) → Eligibility` (pure function, no DB writes) |

### Decisions locked

- **`on_delete` map:**
  - `Course.level` → `PROTECT` (reference table; deleting a level with courses is a mistake)
  - `Course.category` → `PROTECT`
  - `Course.teacher` → `PROTECT` (preserve enrolment audit trail)
  - `Lesson.course` → `CASCADE` (lessons can't outlive their course)
  - `LessonAttachment.lesson` → `CASCADE`
  - `Enrollment.student` → `CASCADE` (student gone → enrolments gone)
  - `Enrollment.course` → `PROTECT`
  - `LessonProgress.enrollment` → `CASCADE`
  - `LessonProgress.lesson` → `CASCADE`
  - `StudentProfile.current_level` → `SET_NULL` (cache field; never block level edit over it)
- **`Course.level` is nullable** → "open course" escape hatch.
- **`Course.track` defaults to `"all"`** → most courses are age-agnostic.
- **`Course.teacher` uses `limit_choices_to={"role": "teacher"}`** (admin-only filter) **+ `clean()` validation** (defence in depth, since `limit_choices_to` is not a DB constraint).
- **`Lesson` unique constraints:** `(course, order)` and `(course, slug)` — slugs unique *within* a course, not globally.
- **`LessonAttachment` file-XOR-URL** enforced in `clean()` (MySQL can't express XOR cleanly).
- **`size_bytes` auto-filled** in `LessonAttachment.save()`.
- **`Enrollment` unique on `(student, course)`** — no double-enrol from a double-click.
- **`LessonProgress` unique on `(enrollment, lesson)`** — one progress row per pair.
- **`LessonProgress` hangs off Enrollment, not StudentProfile** — allows re-enrolment with a fresh trail.
- **Levels seeded by data migration**, not fixture, so any fresh DB gets A1–C2 automatically with no manual `loaddata` step.
- **Eligibility lives in `services.py`** as a pure function returning an `Eligibility` dataclass (`ok`, `reason`, `message`). DB-write decisions (creating `Enrollment` row, "already enrolled" check) stay in views.

### Key technical notes

- **Cross-app FK pattern:** `models.ForeignKey("curriculum.Level", ...)` — string reference avoids circular imports between `accounts` and `curriculum`.
- **Why `current_level` is cached, not computed:** computing on every read would mean joining `Enrollment` × `LessonProgress` × `Course.level` on every page. Cache + write-on-event (placement / certificate / admin) is correct here.
- **Data migration uses `apps.get_model("curriculum", "Level")`** — never `from .models import Level` — so renaming/removing fields later doesn't break replay on fresh DBs.
- **Admin inlines + autocomplete:** `LessonInline` on `CourseAdmin`, `LessonAttachmentInline` on `LessonAdmin`. `autocomplete_fields = ("teacher", "level", "category")` requires `search_fields` on the related admin (already declared on Level / Category / User).
- **`Eligibility` dataclass:** `ok` for branching, `reason` (stable code) for analytics/i18n, `message` (human string) for UI.

### Verifications passed

- `python manage.py check` — 0 issues after each sub-phase (4A, 4B, 4C, 4D, 4E, 4F).
- `python manage.py makemigrations` — 2 migrations generated (curriculum/0001, accounts/0002).
- `python manage.py migrate` — both applied cleanly; `0002_seed_levels` ran without error.
- Admin `/admin/` — Curriculum section visible with all 7 models. A1 → C2 listed in Levels.
- Shell smoke test — `from curriculum.services import student_can_enroll` imports, docstring prints.

### Where to pick up — Phase 5 (Bootstrap UI)

Sub-phases:

- **5A** — base template: navbar, footer, brand from `SITE_NAME`, Bootstrap 5 + Bootstrap Icons via CDN, RTL-ready layout, static files convention
- **5B** — public catalogue: `/courses/` list with filters (level, category, track), `/courses/<slug>/` detail page
- **5C** — lesson player: `/courses/<slug>/lessons/<lesson-slug>/`, gated by enrolment + free-preview check
- **5D** — auth pages: signup (with role + age track for students), login, logout, password reset
- **5E** — dashboards: `/dashboard/` route that branches by role (student / teacher / parent)

---

## Session 1 · 2026-04-29 → 2026-05-01

**Coverage:** Phase 1 design (locked) → Phase 2 scaffold → Phase 3 accounts app
**Status at end:** Phase 3 complete (admin works, signal verified). Phase 4 next.

### Decisions locked

- **Modern Standard Arabic only** (dialect entity removed).
- **Sequential levels** (A1 → C2). Any age can take any level. `age_track` only changes content style.
- **Open courses allowed** — `Course.level_id` nullable, `Course.track` may be `"all"`.
- **Placement test** = special `Quiz.kind` that writes `StudentProfile.current_level`.
- **`current_level` is CACHED**, not computed. Set by certificate / placement / admin override.
- **Schema = 11 tables for MVP** (4 accounts + 7 curriculum). Lesson supports body markdown + 1 primary video URL + many `LessonAttachment` (audio / pdf / docx / pptx / image), each either uploaded file OR external URL.
- **Naming layers:** `Learn_Arabic_Online/` (top folder, renameable) · `core/` (Django module, never renamed) · `SITE_NAME` env var (brand).

### What was built — file by file

| File | Status | Purpose |
|------|--------|---------|
| `.env` | created | secrets — DB credentials, SECRET_KEY, SITE_NAME |
| `.env.example` | created | committable template |
| `.gitignore` | created | excludes `.env`, `venv/`, `__pycache__`, `media/` |
| `core/settings.py` | refactored | reads from `.env` via python-decouple; MySQL OPTIONS = utf8mb4 + STRICT_TRANS_TABLES; `AUTH_USER_MODEL = 'accounts.User'`; `'accounts'` in INSTALLED_APPS |
| `accounts/models.py` | written | `User` (AbstractUser, email-as-username, role TextChoices) + `UserManager` + `TeacherProfile` + `StudentProfile` + `ParentProfile` |
| `accounts/signals.py` | created | `post_save` → auto-create matching profile from `User.role` |
| `accounts/apps.py` | updated | `AccountsConfig.ready()` imports signals so handlers register at startup |
| `accounts/admin.py` | written | custom `UserAdmin` (drops username, adds role) + `UserAdminCreationForm` / `UserAdminChangeForm` + 3 profile admins |
| `accounts/migrations/0001_initial.py` | generated | first migration covering all 4 accounts tables |

### Key technical notes

- **Database charset is `utf8mb4 / utf8mb4_unicode_ci`** — required for Arabic.
- **Settings has MySQL OPTIONS** with `'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"` to refuse silent truncation.
- **Custom User pattern:**
  - `username = None` to drop the inherited field
  - `email = models.EmailField(unique=True)` overrides the inherited (non-unique) email
  - `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`
  - `UserManager` inherits `BaseUserManager`; `_create_user` is the only place `set_password()` runs
- **`AUTH_USER_MODEL` must be set BEFORE first migration**. We dropped+recreated the DB to comply.
- **Signal pattern:** signals live in `accounts/signals.py`, registered via `AppConfig.ready()` (NOT in models.py). Uses `get_or_create()` for idempotency, and skips when `created=False`.
- **Custom UserAdmin requires custom forms** because Django's defaults reference `username`. We subclassed `UserCreationForm` / `UserChangeForm` with `fields = ("email", "role")` / `"__all__"`.
- **Profile FK choices:** `User → Profile` is `OneToOneField(on_delete=CASCADE)`. `StudentProfile.parent → ParentProfile` is `ForeignKey(on_delete=SET_NULL, null=True)` — deleting a parent doesn't wipe the kid.

### Verifications passed

- `python manage.py check` — 0 issues after each phase.
- `python manage.py migrate` — all migrations applied, DB has expected tables.
- `python manage.py createsuperuser` — works with email + password only (no username prompt).
- Admin login at `/admin/` — works. Users + 3 profile sections visible.
- Signal smoke test — creating a User with role=teacher in admin auto-creates a TeacherProfile row. Repeated for student and parent. Admin role correctly creates no profile.

### Where to pick up — Phase 4 (curriculum app)

```bash
python manage.py startapp curriculum
```

Then add `'curriculum'` to `INSTALLED_APPS` and write models in this order (each in `curriculum/models.py`):

1. **Level** — `code` (A1..C2 unique), `name`, `order` (int, gates progression), `description`.
2. **Category** — `slug`, `name`, `description` (Grammar, Reading, Listening, …).
3. **Course** — `title`, `slug`, `level` (FK nullable → open course), `category` (FK), `track` (CharField with choices including `"all"`), `teacher` (FK to `accounts.User`), `is_published`, denormalized `lesson_count` + `enrollment_count`.
4. **Lesson** — `course` (FK), `order`, `title`, `slug`, `body_markdown`, `primary_video_url`, `duration_minutes`, `is_free_preview`.
5. **LessonAttachment** — `lesson` (FK), `kind` (audio/pdf/docx/pptx/image/video/other), `file` (FileField, optional), `external_url` (URL, optional), `order`, `is_downloadable`. Constraint in `clean()`: must have file OR external_url, not both, not neither.
6. **Enrollment** — `student` (FK to `StudentProfile`), `course` (FK), `status`, `started_at`, `completed_at`, `certificate_url`. `unique_together = (student, course)`.
7. **LessonProgress** — `enrollment` (FK), `lesson` (FK), `status`, `last_viewed_at`, `completed_at`. `unique_together = (enrollment, lesson)`.

After models are in:

- Add `MEDIA_ROOT = BASE_DIR / 'media'` and `MEDIA_URL = '/media/'` to settings.
- Update `core/urls.py` to serve `/media/` in dev (via `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` when `DEBUG`).
- Add `current_level = models.ForeignKey('curriculum.Level', null=True, blank=True, on_delete=SET_NULL)` to `accounts.StudentProfile` — separate migration after curriculum exists.
- Register everything in `curriculum/admin.py`.
- Write helper: `student_can_enroll(student, course)` that checks (a) level prereq, (b) open course exception, (c) age track match.
- Seed `Level` rows (A1..C2) via a data migration or fixture.

### Future phases

| Phase | Scope |
|-------|-------|
| 5 | Bootstrap UI — public catalogue, course detail, lesson player, student / teacher dashboards |
| 6 | Assessments — Quiz, Question, Choice, Submission, auto-grade MCQ/TF, certificate generation |
| 7 | Placement test as `Quiz.kind = "placement"` writing `current_level` |
| 8 | Billing — Subscription, Plan, PaymentEvent, household plans |
| 9 | Games & Flashcards — `Game.config` JSON, small JS module per game type |

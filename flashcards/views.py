"""
flashcards/views.py

  GET  /decks/<id>/                      deck_intro       (overview + Start)
  GET  /decks/<id>/study/                study_session    (one card per page)
  POST /decks/<id>/study/                study_session    (record + advance)
  GET  /decks/<id>/summary/              deck_summary     (after a session)
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .models import Flashcard, FlashcardDeck, FlashcardReview
from .services import mark_review


# =========================================================
# Helpers
# =========================================================
def _get_student(request):
    """Return the StudentProfile, or raise 404 for non-students."""
    if not request.user.is_student:
        raise Http404("Only students can study flashcards.")
    student = getattr(request.user, "student_profile", None)
    if student is None:
        raise Http404("Student profile missing.")
    return student


# =========================================================
# Deck intro — /decks/<id>/
# =========================================================
@login_required
def deck_intro(request, deck_id):
    """
    Landing page for a deck. Shows card count, the student's mastery
    progress, and a Start button.
    """
    student = _get_student(request)
    deck = get_object_or_404(
        FlashcardDeck.objects.select_related("lesson", "lesson__course"),
        pk=deck_id,
        is_published=True,
    )

    cards = list(deck.cards.order_by("order"))
    card_ids = [c.id for c in cards]

    # Student's progress on this deck.
    review_map = {
        r.flashcard_id: r
        for r in FlashcardReview.objects.filter(
            student=student, flashcard_id__in=card_ids
        )
    }
    mastered_count = sum(1 for r in review_map.values() if r.is_mastered)
    seen_count = sum(1 for r in review_map.values() if r.times_seen > 0)

    return render(request, "flashcards/deck_intro.html", {
        "deck": deck,
        "cards": cards,
        "total": len(cards),
        "mastered_count": mastered_count,
        "seen_count": seen_count,
    })


# =========================================================
# Study session — /decks/<id>/study/?i=<index>
# =========================================================
@login_required
def study_session(request, deck_id):
    """
    Walk through the cards one at a time.

    GET  ?i=N              -> render card at position N (0-based)
    POST  with action=got/miss + i=N
                           -> record the review, redirect to ?i=N+1

    When the index runs past the last card, redirect to the summary.
    """
    student = _get_student(request)
    deck = get_object_or_404(FlashcardDeck, pk=deck_id, is_published=True)
    cards = list(deck.cards.order_by("order"))
    if not cards:
        raise Http404("This deck has no cards.")

    if request.method == "POST":
        try:
            i = int(request.POST.get("i", 0))
        except (TypeError, ValueError):
            i = 0
        action = request.POST.get("action")

        if 0 <= i < len(cards) and action in ("got", "miss"):
            mark_review(student, cards[i], got_it=(action == "got"))

        next_i = i + 1
        if next_i >= len(cards):
            return HttpResponseRedirect(
                reverse("flashcards:deck_summary", args=[deck.id])
            )
        return HttpResponseRedirect(
            reverse("flashcards:study_session", args=[deck.id])
            + f"?i={next_i}"
        )

    # GET
    try:
        i = int(request.GET.get("i", 0))
    except (TypeError, ValueError):
        i = 0
    if i < 0 or i >= len(cards):
        return HttpResponseRedirect(
            reverse("flashcards:deck_summary", args=[deck.id])
        )

    card = cards[i]

    return render(request, "flashcards/study.html", {
        "deck": deck,
        "card": card,
        "index": i,
        "total": len(cards),
        "is_last": (i == len(cards) - 1),
    })


# =========================================================
# Games — /decks/<id>/match/  and  /decks/<id>/sprint/
# =========================================================
import json
import random

from django.contrib import messages


@login_required
def match_game(request, deck_id):
    """
    Memory-match game.

    Each card becomes two tiles (front + back). They're shuffled and
    rendered face-down; the player flips two at a time, keeping pairs
    that share a card_id. Pure client-side gameplay.

    For decks with many cards, we cap at 8 (= 16 tiles, fits 4x4 grid).
    Other cards are skipped this round; the player can replay to get
    different ones.
    """
    student = _get_student(request)
    deck = get_object_or_404(
        FlashcardDeck.objects.select_related("lesson", "lesson__course"),
        pk=deck_id,
        is_published=True,
    )

    cards = list(deck.cards.order_by("order"))
    if not cards:
        raise Http404("This deck has no cards.")

    # Cap to 8 cards (16 tiles, 4x4 grid). Pick a random subset for replay.
    if len(cards) > 8:
        cards = random.sample(cards, 8)

    # Build the tile list — two tiles per card (front + back).
    tiles = []
    for card in cards:
        tiles.append({
            "card_id": card.id,
            "side": "front",
            "content": card.front,
            "lang": card.front_lang,
        })
        tiles.append({
            "card_id": card.id,
            "side": "back",
            "content": card.back,
            "lang": card.back_lang,
        })
    random.shuffle(tiles)

    return render(request, "flashcards/match.html", {
        "deck": deck,
        "tiles_json": json.dumps(tiles),
        "pair_count": len(cards),
    })


# =========================================================
# Translation Sprint game — /decks/<id>/sprint/
# =========================================================
SPRINT_QUESTIONS = 10  # how many questions per round


@login_required
def sprint_game(request, deck_id):
    """
    Quick-fire MCQ. For each question we pick one card and ask either
    Arabic -> English or English -> Arabic (random per question), with
    three distractors drawn from other cards in the same deck.

    Requires a deck with at least 4 cards (we need 1 right + 3 wrong).
    """
    student = _get_student(request)
    deck = get_object_or_404(
        FlashcardDeck.objects.select_related("lesson", "lesson__course"),
        pk=deck_id,
        is_published=True,
    )

    cards = list(deck.cards.order_by("order"))
    if len(cards) < 4:
        messages.warning(
            request,
            f"Sprint mode needs at least 4 cards in the deck "
            f"(this one has {len(cards)}).",
        )
        return HttpResponseRedirect(
            reverse("flashcards:deck_intro", args=[deck.id])
        )

    # Pick up to N question cards.
    question_cards = random.sample(cards, min(SPRINT_QUESTIONS, len(cards)))

    questions = []
    for card in question_cards:
        # Random direction per question.
        front_first = random.choice([True, False])
        if front_first:
            prompt, prompt_lang = card.front, card.front_lang
            answer, answer_lang = card.back, card.back_lang
            wrong_pool = [c.back for c in cards if c.id != card.id]
        else:
            prompt, prompt_lang = card.back, card.back_lang
            answer, answer_lang = card.front, card.front_lang
            wrong_pool = [c.front for c in cards if c.id != card.id]

        # Three unique distractors that aren't the answer.
        random.shuffle(wrong_pool)
        seen = {answer}
        distractors = []
        for w in wrong_pool:
            if w not in seen:
                seen.add(w)
                distractors.append(w)
                if len(distractors) == 3:
                    break
        if len(distractors) < 3:
            # Couldn't build a 4-option question — skip it.
            continue

        choices = distractors + [answer]
        random.shuffle(choices)

        questions.append({
            "prompt": prompt,
            "prompt_lang": prompt_lang,
            "answer": answer,
            "answer_lang": answer_lang,
            "choices": choices,
        })

    return render(request, "flashcards/sprint.html", {
        "deck": deck,
        "questions_json": json.dumps(questions),
        "question_count": len(questions),
    })


# =========================================================
# Session summary — /decks/<id>/summary/
# =========================================================
@login_required
def deck_summary(request, deck_id):
    """
    Post-session summary. Shows mastered/seen/total + a list of cards
    the student missed in their last pass.
    """
    student = _get_student(request)
    deck = get_object_or_404(FlashcardDeck, pk=deck_id, is_published=True)

    cards = list(deck.cards.order_by("order"))
    card_ids = [c.id for c in cards]
    reviews = list(
        FlashcardReview.objects
        .filter(student=student, flashcard_id__in=card_ids)
        .select_related("flashcard")
    )
    review_map = {r.flashcard_id: r for r in reviews}

    mastered = [r for r in reviews if r.is_mastered]
    needs_practice = [
        r for r in reviews
        if not r.is_mastered and r.times_seen > 0
    ]

    return render(request, "flashcards/deck_summary.html", {
        "deck": deck,
        "total": len(cards),
        "mastered_count": len(mastered),
        "needs_practice": needs_practice,
    })


# =========================================================
# Teacher — deck management
# =========================================================
def _require_teacher_deck(request, deck):
    """Return error response if user isn't the deck's lesson's teacher."""
    from accounts.models import User
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")
    if deck.lesson.course.teacher != request.user:
        return HttpResponseForbidden("You can only manage your own decks.")
    return None


@login_required
def deck_create(request):
    """Create a new flashcard deck."""
    from accounts.models import User
    from .forms import DeckForm
    if request.user.role != User.Role.TEACHER:
        return HttpResponseForbidden("Teachers only.")

    lesson_id = request.GET.get("lesson")
    lesson = None
    if lesson_id:
        from curriculum.models import Lesson
        try:
            lesson = Lesson.objects.get(pk=lesson_id, course__teacher=request.user)
        except Lesson.DoesNotExist:
            pass

    if request.method == "POST":
        form = DeckForm(request.POST, teacher=request.user, lesson=lesson)
        if form.is_valid():
            deck = form.save()
            messages.success(request, f'Deck "{deck.title}" created.')
            return HttpResponseRedirect(
                reverse("flashcards:deck_manage", args=[deck.id])
            )
    else:
        form = DeckForm(teacher=request.user, lesson=lesson)

    return render(request, "flashcards/teach/deck_form.html", {
        "form": form,
        "mode": "create",
        "page_title": "New flashcard deck",
    })


@login_required
def deck_edit(request, deck_id):
    """Edit a deck's settings."""
    from .forms import DeckForm
    deck = get_object_or_404(FlashcardDeck, pk=deck_id)
    err = _require_teacher_deck(request, deck)
    if err:
        return err

    if request.method == "POST":
        form = DeckForm(request.POST, instance=deck, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Deck settings saved.")
            return HttpResponseRedirect(
                reverse("flashcards:deck_manage", args=[deck.id])
            )
    else:
        form = DeckForm(instance=deck, teacher=request.user)

    return render(request, "flashcards/teach/deck_form.html", {
        "form": form,
        "deck": deck,
        "mode": "edit",
        "page_title": f"Edit deck — {deck.title}",
    })


@login_required
def deck_manage(request, deck_id):
    """List cards in a deck."""
    deck = get_object_or_404(
        FlashcardDeck.objects.prefetch_related("cards"),
        pk=deck_id,
    )
    err = _require_teacher_deck(request, deck)
    if err:
        return err

    return render(request, "flashcards/teach/deck_manage.html", {
        "deck": deck,
        "cards": deck.cards.order_by("order"),
    })


@login_required
@require_POST
def deck_delete(request, deck_id):
    """Delete a deck and all its cards."""
    deck = get_object_or_404(FlashcardDeck, pk=deck_id)
    err = _require_teacher_deck(request, deck)
    if err:
        return err

    back_url = reverse(
        "curriculum:course_manage",
        args=[deck.lesson.course.slug],
    )
    title = deck.title
    deck.delete()
    messages.success(request, f'Deck "{title}" deleted.')
    return HttpResponseRedirect(back_url)


# =========================================================
# Teacher — card management
# =========================================================
@login_required
def card_create(request, deck_id):
    """Add a card to a deck."""
    from .forms import CardForm
    deck = get_object_or_404(FlashcardDeck, pk=deck_id)
    err = _require_teacher_deck(request, deck)
    if err:
        return err

    next_order = (deck.cards.count() or 0) + 1

    if request.method == "POST":
        form = CardForm(request.POST, request.FILES)
        if form.is_valid():
            card = form.save(commit=False)
            card.deck = deck
            card.save()
            messages.success(request, "Card added.")
            if "add_another" in request.POST:
                return HttpResponseRedirect(
                    reverse("flashcards:card_create", args=[deck.id])
                )
            return HttpResponseRedirect(
                reverse("flashcards:deck_manage", args=[deck.id])
            )
    else:
        form = CardForm(initial={"order": next_order, "front_lang": "ar", "back_lang": "en"})

    return render(request, "flashcards/teach/card_form.html", {
        "form": form,
        "deck": deck,
        "mode": "create",
        "page_title": "Add card",
    })


@login_required
def card_edit(request, deck_id, card_id):
    """Edit a card."""
    from .forms import CardForm
    deck = get_object_or_404(FlashcardDeck, pk=deck_id)
    err = _require_teacher_deck(request, deck)
    if err:
        return err
    card = get_object_or_404(Flashcard, pk=card_id, deck=deck)

    if request.method == "POST":
        form = CardForm(request.POST, request.FILES, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, "Card saved.")
            return HttpResponseRedirect(
                reverse("flashcards:deck_manage", args=[deck.id])
            )
    else:
        form = CardForm(instance=card)

    return render(request, "flashcards/teach/card_form.html", {
        "form": form,
        "deck": deck,
        "card": card,
        "mode": "edit",
        "page_title": "Edit card",
    })


@login_required
@require_POST
def card_delete(request, deck_id, card_id):
    """Delete a card."""
    deck = get_object_or_404(FlashcardDeck, pk=deck_id)
    err = _require_teacher_deck(request, deck)
    if err:
        return err
    card = get_object_or_404(Flashcard, pk=card_id, deck=deck)
    card.delete()
    messages.success(request, "Card deleted.")
    return HttpResponseRedirect(
        reverse("flashcards:deck_manage", args=[deck.id])
    )

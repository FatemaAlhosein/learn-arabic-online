"""
games/views.py
Interactive games (student) + content management (teacher).
"""
import json
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import GameQuestionForm, VocabWordForm
from .models import GameQuestion, VocabWord


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def _student_level(request):
    """Return the student's current Level (or None)."""
    try:
        return request.user.student_profile.current_level
    except Exception:
        return None


def _vocab_qs(request, require_letters=False, require_missing=False):
    """Return active VocabWords, optionally filtered by student level.
    Falls back to all active words if none match the student's level."""
    level = _student_level(request)
    base_qs = VocabWord.objects.filter(is_active=True).select_related("level")

    qs = base_qs.filter(level=level) if level else base_qs
    # Fall back to all words if level filter returns nothing
    if level and not qs.exists():
        qs = base_qs

    if require_letters:
        qs = qs.exclude(letters=[])
    if require_missing:
        qs = qs.exclude(missing_index=None).exclude(wrong_choices=[])
    return qs


def _strip_tashkeel(text):
    """Remove Arabic diacritics (tashkeel) for Word Hunt grid matching."""
    return re.sub(r'[ً-ٰٟ]', '', text)


# ─────────────────────────────────────────────────────────────
#  Helper
# ─────────────────────────────────────────────────────────────
def _teacher_required(request):
    """Return an HttpResponseForbidden if the user is not a teacher/admin."""
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Login required.")
    role = getattr(request.user, "role", None)
    if role not in ("teacher", "admin") and not request.user.is_staff:
        return HttpResponseForbidden("Teacher access required.")
    return None


# ─────────────────────────────────────────────────────────────
#  Student game views
# ─────────────────────────────────────────────────────────────
@login_required
def hub(request):
    return render(request, "games/hub.html")


@login_required
def word_builder(request):
    words = [
        {
            "ar":           w.arabic,
            "en":           w.english,
            "emoji":        w.emoji,
            "letters":      w.letters,
            "contextForms": w.context_forms,
        }
        for w in _vocab_qs(request, require_letters=True)
    ]
    return render(request, "games/word_builder.html",
                  {"words_json": json.dumps(words, ensure_ascii=False)})


@login_required
def match_pairs(request):
    pairs = [
        {"ar": w.arabic, "en": w.english, "emoji": w.emoji}
        for w in _vocab_qs(request)
    ]
    return render(request, "games/match_pairs.html",
                  {"pairs_json": json.dumps(pairs, ensure_ascii=False)})


@login_required
def sentence_builder(request):
    level = _student_level(request)
    qs = GameQuestion.objects.filter(
        game_type=GameQuestion.GameType.SENTENCE_BUILDER,
        is_active=True,
    ).select_related("level")
    if level:
        qs = qs.filter(level=level)

    # Group by level code (A1/A2/etc.) — fallback label "ALL" when no level set
    grouped = {}
    for q in qs:
        key = q.level.code if q.level else "ALL"
        grouped.setdefault(key, []).append({
            "en":    q.english_sentence,
            "emoji": q.emoji,
            "words": q.word_tokens,
        })

    return render(request, "games/sentence_builder.html",
                  {"sentences_json": json.dumps(grouped, ensure_ascii=False)})


@login_required
def missing_letter(request):
    words = [
        {
            "letters": w.letters,
            "ar":      w.arabic,
            "en":      w.english,
            "emoji":   w.emoji,
            "miss":    w.missing_index,
            "choices": [w.letters[w.missing_index]] + w.wrong_choices,
        }
        for w in _vocab_qs(request, require_letters=True, require_missing=True)
    ]
    return render(request, "games/missing_letter.html",
                  {"words_json": json.dumps(words, ensure_ascii=False)})


@login_required
def true_or_false(request):
    level = _student_level(request)
    qs = GameQuestion.objects.filter(
        game_type=GameQuestion.GameType.TRUE_OR_FALSE,
        is_active=True,
        is_true__isnull=False,
    ).select_related("level")
    if level:
        qs = qs.filter(level=level)

    questions = [
        {
            "emoji":  q.emoji,
            "ar":     q.arabic_sentence,
            "en":     q.english_sentence,
            "answer": q.is_true,
        }
        for q in qs
    ]
    return render(request, "games/true_or_false.html",
                  {"questions_json": json.dumps(questions, ensure_ascii=False)})


@login_required
def word_hunt(request):
    words = [
        {
            "ar":    _strip_tashkeel(w.arabic),
            "en":    w.english,
            "emoji": w.emoji,
        }
        for w in _vocab_qs(request)
        if len(_strip_tashkeel(w.arabic)) >= 2
    ]
    # Word Hunt only uses up to 10 words per grid
    words = words[:10]
    return render(request, "games/word_hunt.html",
                  {"words_json": json.dumps(words, ensure_ascii=False)})


# ─────────────────────────────────────────────────────────────
#  Teacher — Vocabulary management
# ─────────────────────────────────────────────────────────────
@login_required
def vocab_list(request):
    """Teacher: list all vocab words with filter by level."""
    denied = _teacher_required(request)
    if denied:
        return denied

    level_filter  = request.GET.get("level", "")
    active_filter = request.GET.get("active", "")

    qs = VocabWord.objects.select_related("level", "course").order_by("level__order", "english")
    if level_filter:
        qs = qs.filter(level__code=level_filter)
    if active_filter == "1":
        qs = qs.filter(is_active=True)
    elif active_filter == "0":
        qs = qs.filter(is_active=False)

    from curriculum.models import Level
    levels = Level.objects.all()

    return render(request, "games/teach/vocab_list.html", {
        "words":         qs,
        "levels":        levels,
        "level_filter":  level_filter,
        "active_filter": active_filter,
    })


@login_required
def vocab_create(request):
    denied = _teacher_required(request)
    if denied:
        return denied

    form = VocabWordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        word = form.save(commit=False)
        word.created_by = request.user
        word.save()
        messages.success(request, f'Word “{word.arabic}” added successfully.')
        if "add_another" in request.POST:
            return redirect("games:vocab_create")
        return redirect("games:vocab_list")

    return render(request, "games/teach/vocab_form.html", {
        "form":  form,
        "title": "Add vocabulary word",
    })


@login_required
def vocab_edit(request, word_id):
    denied = _teacher_required(request)
    if denied:
        return denied

    word = get_object_or_404(VocabWord, pk=word_id)
    form = VocabWordForm(request.POST or None, instance=word)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f'Word "{word.arabic}" updated.')
        return redirect("games:vocab_list")

    return render(request, "games/teach/vocab_form.html", {
        "form":  form,
        "word":  word,
        "title": f"Edit — {word.arabic}",
    })


@login_required
@require_POST
def vocab_delete(request, word_id):
    denied = _teacher_required(request)
    if denied:
        return denied

    word = get_object_or_404(VocabWord, pk=word_id)
    label = word.arabic
    word.delete()
    messages.success(request, f'Word "{label}" deleted.')
    return redirect("games:vocab_list")


# ─────────────────────────────────────────────────────────────
#  Teacher — Game Questions management
# ─────────────────────────────────────────────────────────────
@login_required
def question_list(request):
    denied = _teacher_required(request)
    if denied:
        return denied

    game_filter  = request.GET.get("game", "")
    level_filter = request.GET.get("level", "")

    qs = GameQuestion.objects.select_related("level", "course").order_by("level__order", "game_type", "id")
    if game_filter:
        qs = qs.filter(game_type=game_filter)
    if level_filter:
        qs = qs.filter(level__code=level_filter)

    from curriculum.models import Level
    levels = Level.objects.all()

    return render(request, "games/teach/question_list.html", {
        "questions":    qs,
        "levels":       levels,
        "game_choices": GameQuestion.GameType.choices,
        "game_filter":  game_filter,
        "level_filter": level_filter,
    })


@login_required
def question_create(request):
    denied = _teacher_required(request)
    if denied:
        return denied

    form = GameQuestionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        q = form.save(commit=False)
        q.created_by = request.user
        q.save()
        messages.success(request, "Question added successfully.")
        if "add_another" in request.POST:
            return redirect("games:question_create")
        return redirect("games:question_list")

    return render(request, "games/teach/question_form.html", {
        "form":  form,
        "title": "Add game question",
    })


@login_required
def question_edit(request, question_id):
    denied = _teacher_required(request)
    if denied:
        return denied

    question = get_object_or_404(GameQuestion, pk=question_id)
    form = GameQuestionForm(request.POST or None, instance=question)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Question updated.")
        return redirect("games:question_list")

    return render(request, "games/teach/question_form.html", {
        "form":     form,
        "question": question,
        "title":    "Edit question",
    })


@login_required
@require_POST
def question_delete(request, question_id):
    denied = _teacher_required(request)
    if denied:
        return denied

    question = get_object_or_404(GameQuestion, pk=question_id)
    question.delete()
    messages.success(request, "Question deleted.")
    return redirect("games:question_list")

"""Server-side scoring for exercise submissions.

Progress is now driven by scores, so the score stored must be one the server
can stand behind, not whatever number the browser sends. For question-based
exercises the answers are re-checked here against the Question rows; for the
rest the submitted score is clamped to a valid range.

    mcq         re-graded: chosen option vs Question.correct_answer
    fill_blank  re-graded: typed answer vs Question.correct_answer
                (trimmed, case-insensitive — same rule as the page)
    matching    re-graded: each term's paired definition vs its own
    ordering    re-counted from the submitted placements
    bingo       re-counted: only rounds whose pick matches the target word
                and is a real card on this exercise
    writing /   AI-scored on the server when SARVAM_API_KEY is set
    timer       (see submit_exercise); otherwise clamped to 0..max

Question numbering follows the page: answers are keyed "1", "2", ... in the
order of exercise.questions.all().
"""

from __future__ import annotations


def _norm(value) -> str:
    return str(value if value is not None else '').strip().lower()


def _clamp(score, max_score):
    try:
        max_score = max(0, int(round(float(max_score))))
    except (TypeError, ValueError):
        max_score = 0
    try:
        score = int(round(float(score)))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(score, max_score)), max_score


def _answer(answers, number):
    entry = answers.get(str(number))
    if entry is None:
        entry = answers.get(number)
    return entry if isinstance(entry, dict) else {}


def grade_submission(exercise, score, max_score, answers):
    """Return (score, max_score) the server accepts for this submission."""
    answers = answers if isinstance(answers, dict) else {}
    kind = exercise.exercise_type
    questions = list(exercise.questions.all())
    n = len(questions)

    if kind == 'mcq' and n:
        correct = sum(
            1 for i, q in enumerate(questions, start=1)
            if _norm(_answer(answers, i).get('chosen')) == _norm(q.correct_answer)
            and _norm(q.correct_answer)
        )
        return correct, n

    if kind == 'fill_blank' and n:
        correct = sum(
            1 for i, q in enumerate(questions, start=1)
            if _norm(_answer(answers, i).get('given')) == _norm(q.correct_answer)
            and _norm(q.correct_answer)
        )
        return correct, n

    if kind == 'matching' and n:
        # Left and right items share the same number; a term is matched
        # correctly when it was paired with the definition of the same number.
        correct = sum(
            1 for i in range(1, n + 1)
            if _norm(_answer(answers, i).get('paired')) == str(i)
        )
        return correct, n

    if kind == 'ordering' and n:
        correct = 0
        for i in range(1, n + 1):
            entry = _answer(answers, i)
            if entry and _norm(entry.get('placed')) == _norm(entry.get('correct')) != '':
                correct += 1
        return correct, n

    if kind == 'bingo':
        words = {_norm(w) for w in exercise.bingo_cards.values_list('word', flat=True)}
        rounds = [v for k, v in answers.items() if str(k).startswith('w') and isinstance(v, dict)]
        correct = sum(
            1 for r in rounds
            if _norm(r.get('chosen')) and _norm(r.get('chosen')) == _norm(r.get('target'))
            and _norm(r.get('chosen')) in words
        )
        # Rounds played can't exceed the cards on the board (max 25).
        card_count = min(len(words), 25) or 0
        _, claimed_max = _clamp(0, max_score)
        total = min(max(claimed_max, len(rounds), correct), card_count) if card_count else claimed_max
        return min(correct, total), total

    if kind == 'timer' and n:
        # The page scores timed tasks out of the number of tasks.
        return _clamp(score, n)

    if kind == 'writing':
        return _clamp(score, 100)

    return _clamp(score, max_score)

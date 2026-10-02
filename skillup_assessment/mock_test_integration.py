"""
Mock Test integration point.

Real, server-persisted quiz history now exists (skillup_assessment.models.
QuizAttempt), written by activities.views' three submit endpoints
(quiz_submit, amcat_submit, cocubes_submit) every time an authenticated
user submits a quiz. This is the ONE place Certifications reaches into
that history -- nothing else in this app should know or care how a score
is stored.

Retake policy: the BEST (highest percentage) attempt on record counts,
matching the "TOP SCORE" concept already shown on the standalone Mock Test
pages (static/001 Career Buddy/TechCenter/*_mock_test.html). A later,
lower-scoring retake never revokes eligibility already earned by a better
attempt (spec section 19/13: don't let retakes "un-earn" a passing result).
"""
from .models import QuizAttempt

PASS_THRESHOLD_PCT = 70  # spec: score >= 70 -> eligible (70 itself DOES pass)


def get_mock_test_result(user, subject):
    """Return the user's best-ever result for one certification subject.

    Shape:
        {
            "score": int | None,   # out of `total`; None if never attempted
            "total": int | None,
            "completed": bool,
        }

    "Best" = highest percentage across every QuizAttempt on record for this
    (user, subject) pair -- see module docstring for the retake policy.
    """
    if not user.is_authenticated:
        return {"score": None, "total": None, "completed": False}

    attempts = QuizAttempt.objects.filter(user=user, subject=subject)
    best = None
    for a in attempts:
        if best is None or a.percentage > best.percentage:
            best = a

    if best is None:
        return {"score": None, "total": None, "completed": False}

    return {"score": best.score, "total": best.total, "completed": True}


def is_eligible(mock_test_result):
    """percentage >= 70 -> eligible; < 70 or not completed -> not eligible.

    Compares PERCENTAGE (score/total), not raw score, against the
    threshold -- necessary since `total` varies per subject (a 50-question
    test vs a 20-question test). Threshold is INCLUSIVE: exactly 70% must
    pass (spec section 2 is explicit that `score > 70` is wrong; must be
    `score >= 70`).
    """
    if not mock_test_result.get("completed"):
        return False
    score = mock_test_result.get("score")
    total = mock_test_result.get("total")
    if score is None or not total:
        return False
    percentage = (score / total) * 100
    return percentage >= PASS_THRESHOLD_PCT

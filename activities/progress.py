"""Performance-based progress for the Activities module.

This is the ONE place progress is calculated. The dashboard, the Activities
list, the activity page, the sub-activity page and the submit response all
read from here, so they always agree.

The rule
--------
* Exercise      = the user's score as a percentage (correct / total).
                  10 questions, 7 correct -> 70%.
* Sub-activity  = average of its exercises' percentages.
* Activity      = average of ALL its exercises' percentages.
  An exercise the user has not attempted yet counts as 0%, so an activity is
  only at 100% when every exercise in it has been done perfectly.
* Workshops (Group Discussion, JAM, Role Play) have no fixed exercise list;
  their progress is the user's session score from ScoreRecord.

Which attempt counts
--------------------
settings.ACTIVITY_PROGRESS_SCORING:
  'latest' (default) - the most recent attempt: progress shows the user's
                       CURRENT level and goes down as well as up.
  'best'             - the highest attempt: progress never goes down.

Status (Not started / In progress / Completed) is separate from the
percentage and describes coverage only: "Completed" means every exercise has
been attempted; the percentage says how well.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

# Colour bands — the same thresholds the per-exercise score badges already use.
BAND_GOOD = 80
BAND_FAIR = 50

WORKSHOP_MODULES = ('gd', 'jam', 'roleplay')


def scoring_policy() -> str:
    policy = str(getattr(settings, 'ACTIVITY_PROGRESS_SCORING', 'latest')).lower()
    return policy if policy in ('latest', 'best') else 'latest'


def _round(value: float) -> int:
    # Half-up rounding (Python's round() is banker's rounding: 72.5 -> 72).
    return int(value + 0.5)


def to_percent(score, max_score) -> float:
    """score/max_score as 0-100, clamped. 0 when there is no max."""
    try:
        score = float(score or 0)
        max_score = float(max_score or 0)
    except (TypeError, ValueError):
        return 0.0
    if max_score <= 0:
        return 0.0
    return max(0.0, min(100.0, score * 100.0 / max_score))


@dataclass(frozen=True)
class Progress:
    percent: int = 0          # performance, 0-100
    attempted: int = 0        # exercises (or sessions) with at least one result
    total: int = 0            # exercises in scope
    scored: bool = True       # False when there is nothing measurable

    @property
    def status(self) -> str:
        if self.attempted == 0:
            return 'not_started'
        if self.total and self.attempted >= self.total:
            return 'completed'
        return 'in_progress'

    @property
    def band(self) -> str:
        """Bootstrap colour for the bar / label."""
        if self.attempted == 0:
            return 'secondary'
        if self.percent >= BAND_GOOD:
            return 'success'
        if self.percent >= BAND_FAIR:
            return 'warning'
        return 'danger'

    def as_dict(self) -> dict:
        return {
            'percent': self.percent,
            'attempted': self.attempted,
            'total': self.total,
            'status': self.status,
            'band': self.band,
        }


EMPTY = Progress(scored=False)


# --------------------------------------------------------------------------- #
#  Exercise level
# --------------------------------------------------------------------------- #

def exercise_percentages(user, exercise_ids=None) -> dict:
    """{exercise_id: percent} for every exercise the user has a result for.

    One query. Uses the latest or best attempt per settings.
    """
    if not getattr(user, 'is_authenticated', False):
        return {}
    from .models import UserExerciseResult

    qs = UserExerciseResult.objects.filter(user=user)
    if exercise_ids is not None:
        exercise_ids = list(exercise_ids)
        if not exercise_ids:
            return {}
        qs = qs.filter(exercise_id__in=exercise_ids)

    best = scoring_policy() == 'best'
    out: dict = {}
    rows = qs.order_by('exercise_id', '-completed_at', '-id').values_list(
        'exercise_id', 'score', 'max_score'
    )
    for ex_id, score, max_score in rows:
        pct = to_percent(score, max_score)
        if ex_id not in out:
            out[ex_id] = pct          # first row per exercise = latest attempt
        elif best and pct > out[ex_id]:
            out[ex_id] = pct
    return out


def summarize(exercise_ids, pct_map) -> Progress:
    """Average performance over `exercise_ids`; unattempted count as 0%."""
    ids = list(exercise_ids)
    if not ids:
        return EMPTY
    attempted = sum(1 for i in ids if i in pct_map)
    avg = sum(pct_map.get(i, 0.0) for i in ids) / len(ids)
    return Progress(percent=_round(avg), attempted=attempted, total=len(ids))


# --------------------------------------------------------------------------- #
#  Sub-activity / activity level
#  Pass objects with subactivities/exercises prefetched to avoid N+1 queries.
# --------------------------------------------------------------------------- #

def sub_activity_exercise_ids(sub) -> list:
    return [e.id for e in sub.exercises.all()]


def activity_exercise_ids(activity) -> list:
    return [e.id for s in activity.subactivities.all() for e in s.exercises.all()]


def sub_activity_progress(sub, pct_map) -> Progress:
    return summarize(sub_activity_exercise_ids(sub), pct_map)


def activity_progress(activity, pct_map, workshop_map=None) -> Progress:
    if activity.category == 'workshop':
        key = workshop_key(activity)
        if workshop_map is None:
            return EMPTY
        return workshop_map.get(key, Progress(total=1)) if key else EMPTY
    return summarize(activity_exercise_ids(activity), pct_map)


# --------------------------------------------------------------------------- #
#  Workshops (GD / JAM / Role Play) — scored per session in core.ScoreRecord
# --------------------------------------------------------------------------- #

def workshop_key(activity):
    title = (activity.title or '').lower()
    if 'group discussion' in title or title == 'gd':
        return 'gd'
    if 'jam' in title:
        return 'jam'
    if 'role play' in title or 'roleplay' in title:
        return 'roleplay'
    return None


def workshop_progress(user) -> dict:
    """{module: Progress} from the user's workshop sessions.

    Workshops are open-ended practice (any number of topics), so there is no
    "all exercises done": status is In progress once a session exists, and
    the percentage is the latest (or best) session score.
    """
    if not getattr(user, 'is_authenticated', False):
        return {}
    from core.models import ScoreRecord

    best = scoring_policy() == 'best'
    pct: dict = {}
    count: dict = {}
    rows = (
        ScoreRecord.objects.filter(user=user, module__in=WORKSHOP_MODULES)
        .order_by('module', '-created_at', '-id')
        .values_list('module', 'score', 'max_score')
    )
    for module, score, max_score in rows:
        p = to_percent(score, max_score)
        count[module] = count.get(module, 0) + 1
        if module not in pct:
            pct[module] = p
        elif best and p > pct[module]:
            pct[module] = p
    # total is left 0 so status stays 'in_progress', never 'completed'.
    return {m: Progress(percent=_round(pct[m]), attempted=count[m], total=0) for m in pct}


# --------------------------------------------------------------------------- #
#  Convenience for views that need one activity
# --------------------------------------------------------------------------- #

def progress_for_activity(user, activity) -> Progress:
    if activity.category == 'workshop':
        return activity_progress(activity, {}, workshop_progress(user))
    ids = activity_exercise_ids(activity)
    return summarize(ids, exercise_percentages(user, ids))


def progress_for_sub_activity(user, sub) -> Progress:
    ids = sub_activity_exercise_ids(sub)
    return summarize(ids, exercise_percentages(user, ids))

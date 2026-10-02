import json
import logging
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q, Prefetch
from .models import (
    Activity, SubActivity, Exercise, Question, BingoCard,
    UserProgress, UserExerciseResult, FreeActivitySelection,
)
from . import progress as perf
from .grading import grade_submission

# Sentinel so callers can pass selection=None ("no selection") distinctly from
# "not supplied, go and look it up".
_UNSET = object()

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #

def get_module_template(activity):
    """Return the specialised AI module template path based on activity title/category keywords, or None."""
    title = activity.title.lower()
    # speaking module matches
    if "speaking" in title and "professional" in title:
        return 'activities/modules/speaking.html'
    # writing module matches (e.g. "Professional Passage Writing" or "Professional Writing")
    if "writing" in title and "professional" in title:
        return 'activities/modules/writing.html'
    # reading module matches
    if "reading" in title and "professional" in title:
        return 'activities/modules/reading.html'
    # listening module matches (e.g. "Listen & Learn")
    if "listen" in title:
        return 'activities/modules/listening.html'
    return None

def is_module_activity(activity):
    """Check if activity should skip sub-activity list and go direct to exercise."""
    return get_module_template(activity) is not None

def is_workshop_activity(activity):
    """Check if activity is a workshop type (GD/JAM/Roleplay) that has its own app."""
    return activity.category == 'workshop'

def get_workshop_url(activity):
    """Return the direct URL for a workshop activity based on its title."""
    title_lower = activity.title.lower()
    if 'group discussion' in title_lower or 'gd' == title_lower:
        return '/gd/'
    elif 'jam' in title_lower:
        return '/jam/'
    elif 'role play' in title_lower or 'roleplay' in title_lower:
        return '/roleplay/'
    return None

# Maps activity category -> which agent/module to use
CATEGORY_TO_MODULE = {
    'speaking': 'speaking',
    'writing':  'writing',
    'listening':'listening',
    'reading':  'reading',
}


# --------------------------------------------------------------------------- #
#  Public views
# --------------------------------------------------------------------------- #

def home(request):
    if request.user.is_authenticated and (request.session.get('portal') == 'employer' or hasattr(request.user, 'employer_profile')):
        return redirect('job_home')

    activities = Activity.objects.filter(is_active=True).exclude(
        title__iexact="Professional Speaking"
    ).order_by('order')[:6]
    total_activities = Activity.objects.filter(is_active=True).count()
    context = {
        'featured_activities': activities,
        'total_activities': total_activities,
    }
    return render(request, 'home.html', context)


@login_required
def dashboard(request):
    # BR-03: an employer session must not be able to reach the student
    # dashboard's content — home() above already redirects an employer away
    # from the public landing page the same way, but this view (the actual
    # /dashboard/ the nav bar links to) had no equivalent guard, so a logged
    # in employer could load the student dashboard directly at 200 OK.
    if request.session.get('portal') == 'employer' or hasattr(request.user, 'employer_profile'):
        return redirect('job_home')

    # Explicit .order_by('order') rather than relying solely on Activity.Meta's
    # default ordering — makes the numbered activity list deterministic
    # regardless of environment/DB quirks or future query changes upstream
    # that could otherwise silently drop the implicit ordering.
    #
    # Subactivities + exercises are prefetched (both ordered, matching the
    # queries this replaces below) so the per-activity loop reads already
    # fetched data instead of re-querying per activity/subactivity — this was
    # a severe N+1 (188 queries for one dashboard load, profiled locally with
    # CaptureQueriesContext: subs.count() alone re-queried per activity even
    # though subactivities were already prefetched, plus 2 queries per
    # subactivity from all_exercises_done(), plus 1 query per module activity
    # for its direct-launch exercise, plus 1 query per activity for
    # started_at).
    activities = list(
        Activity.objects.filter(is_active=True).order_by('order').prefetch_related(
            Prefetch(
                'subactivities',
                queryset=SubActivity.objects.order_by('order').prefetch_related(
                    Prefetch('exercises', queryset=Exercise.objects.order_by('order'))
                ),
            )
        )
    )
    user_progress = list(
        UserProgress.objects.filter(user=request.user).select_related('sub_activity__activity')
    )

    # Earliest started_at per activity, across all its subactivities' progress
    # rows — replaces the per-activity
    # user_progress.filter(sub_activity__activity=activity, started_at__isnull=False)
    #   .order_by('started_at').first() query.
    started_at_by_activity = {}
    for p in user_progress:
        if p.started_at is None:
            continue
        activity_id = p.sub_activity.activity_id
        if activity_id not in started_at_by_activity or p.started_at < started_at_by_activity[activity_id]:
            started_at_by_activity[activity_id] = p.started_at

    # Performance-based progress (activities/progress.py): one query for
    # every exercise score, one for workshop sessions.
    pct_map = perf.exercise_percentages(request.user)
    workshop_map = perf.workshop_progress(request.user)

    from core.models import ScoreRecord

    recent_exercise_results = list(UserExerciseResult.objects.filter(
        user=request.user
    ).select_related('exercise__sub_activity__activity').order_by('-completed_at')[:5])

    recent_score_records = list(ScoreRecord.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5])

    unified_recent_results = []
    for r in recent_exercise_results:
        unified_recent_results.append({
            'title': r.exercise.title,
            'activity_name': r.exercise.sub_activity.activity.title,
            'score': r.score,
            'max_score': r.max_score,
            'percentage': r.percentage,
            'date': r.completed_at
        })

    for r in recent_score_records:
        percentage = int((r.score / r.max_score * 100)) if r.max_score else 0
        module_display_name = dict(ScoreRecord.MODULE_CHOICES).get(r.module, r.module.title())
        title_label = r.label or f"{module_display_name} Session"
        for prefix in ["Beginner - ", "Intermediate - ", "Advanced - "]:
            if title_label.startswith(prefix):
                title_label = title_label[len(prefix):]
                break

        unified_recent_results.append({
            'title': title_label,
            'activity_name': module_display_name,
            'score': round(r.score, 1) if r.score % 1 else int(r.score),
            'max_score': int(r.max_score),
            'percentage': percentage,
            'date': r.created_at
        })

    unified_recent_results.sort(key=lambda x: x['date'], reverse=True)
    recent_results = unified_recent_results[:5]

    activities_with_progress = []
    completed_activity_count = 0
    in_progress_activity_count = 0
    from django.urls import reverse
    for activity in activities:
        subs = list(activity.subactivities.all())
        prog = perf.activity_progress(activity, pct_map, workshop_map)
        if prog.status == 'completed':
            completed_activity_count += 1
        elif prog.status == 'in_progress':
            in_progress_activity_count += 1

        # For module-type activities, build a direct link to the exercise —
        # first exercise of the first non-empty subactivity, in order, same
        # as the previous Exercise.objects.filter(sub_activity__activity=activity)
        #   .order_by('sub_activity__order', 'order').first().
        direct_url = None
        if is_module_activity(activity):
            for s in subs:
                exs = list(s.exercises.all())
                if exs:
                    direct_url = reverse('exercise_detail', args=[exs[0].pk])
                    break

        started_at = started_at_by_activity.get(activity.id)

        activities_with_progress.append({
            'activity': activity,
            'progress': prog,
            # Performance percentage (kept under the old key for templates).
            'completion_rate': prog.percent,
            'is_workshop': is_workshop_activity(activity),
            'direct_url': direct_url,
            'started_at': started_at,
        })

    # Overall performance = average of the activities the user has started.
    started = [i['progress'] for i in activities_with_progress if i['progress'].attempted]
    overall_performance = (
        perf.Progress(percent=int(sum(p.percent for p in started) / len(started) + 0.5),
                      attempted=len(started), total=len(activities_with_progress))
        if started else None
    )

    exercise_total = sum(r.score for r in UserExerciseResult.objects.filter(user=request.user))
    score_record_total = sum(sr.score for sr in ScoreRecord.objects.filter(user=request.user))
    total_score = round(exercise_total + score_record_total)

    # Job recommendations, surfaced in the student portal once the candidate has
    # scored above 70 in the AI mock interview. How many they see depends on the
    # plan: Normal (₹499) gets 5, Pro (₹999) unlimited. Imported locally to keep
    # the activities app free of a hard dependency on career_app.
    from career_app.views import (_get_matched_jobs, _job_recommendation_limit,
                                  _can_access_interview)
    from career_app.models import ResumeInterviewSession
    from career_app.resume_utils import extract_experience_years

    passed_session = None
    if _can_access_interview(request.user):
        # Re-checked here so a user who downgrades to Free stops seeing the
        # recommendations their old interview unlocked.
        passed_session = (
            ResumeInterviewSession.objects
            .filter(resume__user=request.user, is_passed=True)
            .select_related('resume')
            .order_by('-start_time')
            .first()
        )

    recommended_jobs = []
    if passed_session:
        recommended_jobs = _get_matched_jobs(
            passed_session.matching_skills or [],
            years_experience=extract_experience_years(passed_session.resume.extracted_text),
            max_results=_job_recommendation_limit(request.user),
        )
        for job in recommended_jobs:
            job.salary_display = job.get_salary_display_for_user(request.user)

    from career_app.models import RazorpayPayment
    from django.utils import timezone
    from datetime import timedelta
    
    payment_history_qs = RazorpayPayment.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    payment_history = []
    now = timezone.now()
    for payment in payment_history_qs:
        # Evaluate if the plan attached to this payment is currently active (within 365 days and captured)
        payment.is_plan_active = (payment.status == RazorpayPayment.STATUS_CAPTURED and (now - payment.created_at).days <= 365)
        payment_history.append(payment)

    context = {
        'payment_history': payment_history,
        'activities_with_progress': activities_with_progress,
        'overall_performance': overall_performance,
        'completed_count': completed_activity_count,
        'in_progress_count': in_progress_activity_count,
        'recent_results': recent_results,
        'total_score': total_score,
        'total_activities': Activity.objects.filter(is_active=True).count(),
        'recommended_jobs': recommended_jobs,
        'interview_score': passed_session.total_score if passed_session else None,
    }
    return render(request, 'dashboard.html', context)



def _has_full_activities_access(user):
    # Read the plan through career_app's resolver rather than off the profile
    # fields: it auto-lapses a subscription whose 1-year window has passed, so a
    # user whose plan expired loses the paid activities on the very next request
    # instead of keeping them until some page happens to trigger the check.
    # Imported locally to keep the activities app free of a hard dependency on
    # career_app.
    from career_app.views import _get_user_plan
    return _get_user_plan(user) in ('normal', 'pro')

# Activities shown on the Free Plan, by Activity.order:
#   22 Listen & Learn
#   23 Professional Reading
#   15 Business Vocabulary Building Games
#   17 Data Presentation and Visualization
# A Free Plan user sees all four and may open ANY ONE of them. Whichever they
# open first is recorded in FreeActivitySelection and stays available; the other
# three lock immediately.
FREE_PLAN_ACTIVITY_TITLES = [
    'Listen & Learn',
    'Professional Reading',
    'Business Vocabulary Building Games',
    'Data Presentation and Visualization'
]


def _is_free_plan_activity(activity):
    """Is this activity shown in the Free Plan catalogue (openable or locked)?"""
    return bool(activity) and activity.title in FREE_PLAN_ACTIVITY_TITLES


def _free_activity_already_worked_on(user):
    """The Free Plan activity this user has real progress in, most recent first.

    A user who earned progress while on a paid plan and later moved to Free has
    already "used" that activity, so it is the one their single free slot should
    be spent on — not whichever card they happen to click next.
    """
    if not user.is_authenticated:
        return None
    progress = (
        UserProgress.objects
        .filter(user=user, sub_activity__activity__title__in=FREE_PLAN_ACTIVITY_TITLES)
        .select_related('sub_activity__activity')
        .order_by('-started_at')
        .first()
    )
    return progress.sub_activity.activity if progress else None


# Only ONE activity is free — the first one the user opens.
FREE_ACTIVITY_LIMIT = 1


def _get_free_selection(user):
    """
    Return the Free Plan activity selections for this user.

    Only returns selections for activities that are CURRENTLY in the
    Free Plan catalogue (FREE_PLAN_ACTIVITY_TITLES). Stale rows that
    point to activities removed from the catalogue are ignored so they
    don't permanently consume the user's free slot.

    A Free user can select exactly ONE activity. The returned value
    is a queryset so callers can check the selected activity ID(s).
    """
    if not user.is_authenticated:
        return FreeActivitySelection.objects.none()

    return (
        FreeActivitySelection.objects
        .filter(user=user, activity__title__in=FREE_PLAN_ACTIVITY_TITLES)
        .select_related('activity')
        .order_by('started_at', 'pk')
    )


def _can_access_activity(user, activity, selection=_UNSET):
    """
    Free Plan users can access exactly ONE activity (their free slot).

    - Pro/full-access users can access everything.
    - Activities outside the Free Plan pool are always locked for Free users.
    - Before any activity has been selected, any Free Plan activity can be opened.
    - Once one has been selected, only that one remains accessible; the rest lock.
    """
    if _has_full_activities_access(user):
        return True

    if not _is_free_plan_activity(activity):
        return False

    if selection is _UNSET:
        selection = _get_free_selection(user)

    # A caller iterating many activities can pass an already-materialized set
    # of activity ids (see activity_list) so this doesn't re-query the
    # selection queryset once per activity.
    if isinstance(selection, (set, frozenset)):
        selected_ids = selection
    else:
        selected_ids = set(
            selection.values_list('activity_id', flat=True)
        )

    # Already selected → always accessible.
    if activity.pk in selected_ids:
        return True

    # Still have free slots → this activity can be selected.
    return len(selected_ids) < FREE_ACTIVITY_LIMIT

# Title keywords identifying each workshop activity - the SAME matching
# logic get_workshop_url() above already uses for navigation, reused here
# so there is exactly one way of identifying these three activities,
# rather than two definitions that can silently drift apart.
_WORKSHOP_TITLE_KEYWORDS = {
    'gd': ('group discussion',),
    'jam': ('jam',),
    'roleplay': ('role play', 'roleplay'),
}


def _can_access_workshop(user, workshop_key):
    """
    Check whether a user can access a workshop activity (Group Discussion,
    JAM, or Roleplay).

    `workshop_key` is 'gd', 'jam', or 'roleplay'. This used to take a
    hardcoded Activity.order number (25/26/27), but the actual order
    values in the live database (40, 41, 102) never matched those - so
    the lookup always found nothing and this function always returned
    False, silently blocking every user, Free or paid, from all three
    activities. Matching by title is stable regardless of what order
    number these activities happen to have.
    """
    from .models import Activity

    keywords = _WORKSHOP_TITLE_KEYWORDS.get(workshop_key, ())
    if not keywords:
        return False

    for activity in Activity.objects.filter(category='workshop', is_active=True):
        title_lower = activity.title.lower()
        if any(keyword in title_lower for keyword in keywords):
            return _can_access_activity(user, activity)

    return False


def _claim_free_activity(user, activity):
    """
    Claim the single Free Plan activity slot.

    Re-opening an already selected activity does nothing.
    A second activity cannot be claimed while the slot is taken.
    Stale selections (activities no longer in the free catalogue) are
    automatically cleared so they don't permanently block the user.
    """
    if not user.is_authenticated:
        return

    if _has_full_activities_access(user):
        return

    if not _is_free_plan_activity(activity):
        return

    existing = FreeActivitySelection.objects.filter(
        user=user,
        activity=activity,
    ).exists()

    if existing:
        return

    # Count only VALID selections (activities still in the free catalogue).
    # Stale rows (e.g. from a previous catalogue configuration) must not
    # permanently block the user from picking any of the current 4 activities.
    valid_selected_count = FreeActivitySelection.objects.filter(
        user=user,
        activity__title__in=FREE_PLAN_ACTIVITY_TITLES,
    ).count()

    if valid_selected_count >= FREE_ACTIVITY_LIMIT:
        return

    FreeActivitySelection.objects.create(
        user=user,
        activity=activity,
    )


def _locked_redirect():
    """Send the user back to the activity list with the upgrade pop-up triggered."""
    from django.urls import reverse
    return redirect(f"{reverse('activity_list')}?locked=1")

@login_required
def activity_list(request):
    is_full_access = _has_full_activities_access(request.user)

    from django.urls import reverse
    category = request.GET.get('category', '')

    # A category that holds exactly one activity (e.g. "listening" = Listen &
    # Learn) has no useful listing to show — open that activity directly. This is
    # what lets the chatbot's "open Listen & Learn" (routed to
    # ?category=listening) land on the activity page itself, for free and paid
    # users alike (activity_detail enforces its own access). Dynamic pk, so it
    # stays correct on a fresh DB.
    if category:
        _cat_acts = Activity.objects.filter(is_active=True, category=category)
        if _cat_acts.count() == 1:
            return redirect('activity_detail', pk=_cat_acts.first().pk)

    # Explicit .order_by('order') rather than relying solely on Activity.Meta's
    # default ordering — same reasoning as dashboard() above.
    activities = Activity.objects.filter(is_active=True).order_by('order')

    if not is_full_access:
        # Free Plan: show the Free Plan catalogue only — locking happens per card below.
        activities = activities.filter(title__in=FREE_PLAN_ACTIVITY_TITLES)
    elif category:
        activities = activities.filter(category=category)
    # "All" now includes the Interactive Workshop activities (Group Discussion,
    # JAM, Role Play). They used to be excluded here, so they only appeared
    # under their own category filter and were missing from the default view.

    # Fetch the Free Plan selection once and reuse it for every card. Passing
    # a materialized set (rather than the queryset) into _can_access_activity
    # below means that check is a single query total, not one per activity.
    free_selection = None if is_full_access else _get_free_selection(request.user)
    free_selected_ids = (
        None if free_selection is None
        else set(free_selection.values_list('activity_id', flat=True))
    )

    # Prefetch every activity's subactivities + exercises (both ordered, same
    # as the per-activity queries this replaces) so the loop below computes
    # completion rate and the direct-launch URL from already-fetched data
    # instead of issuing 2 extra queries per subactivity — this was the
    # dashboard's N+1: 4 activities x 2 subactivities was 8 separate
    # `activities_exercise` queries and 8 separate `activities_userexerciseresult`
    # queries alone (profiled locally with CaptureQueriesContext).
    activities = list(
        activities.prefetch_related(
            Prefetch(
                'subactivities',
                queryset=SubActivity.objects.order_by('order').prefetch_related(
                    Prefetch('exercises', queryset=Exercise.objects.order_by('order'))
                ),
            )
        )
    )

    # Performance-based progress (activities/progress.py).
    pct_map = perf.exercise_percentages(request.user) if request.user.is_authenticated else {}
    workshop_map = perf.workshop_progress(request.user) if request.user.is_authenticated else {}

    activities_data = []
    for activity in activities:
        subs = list(activity.subactivities.all())
        prog = (perf.activity_progress(activity, pct_map, workshop_map)
                if request.user.is_authenticated else perf.EMPTY)

        direct_url = None
        if is_workshop_activity(activity):
            direct_url = get_workshop_url(activity)
        elif is_module_activity(activity):
            # First exercise of the first non-empty subactivity, in order —
            # equivalent to the previous
            # Exercise.objects.filter(sub_activity__activity=activity)
            #   .order_by('sub_activity__order', 'order').first()
            for s in subs:
                exs = list(s.exercises.all())
                if exs:
                    direct_url = reverse('exercise_detail', args=[exs[0].pk])
                    break

        is_locked = not _can_access_activity(request.user, activity, selection=free_selected_ids)
        activities_data.append({
            'activity': activity,
            'progress': prog,
            'completion_rate': prog.percent,
            'direct_url': direct_url,
            'is_locked': is_locked,
        })

    from .models import CATEGORY_CHOICES
    # The single free activity the user has already claimed (if any).
    free_selected_activity = (
        free_selection.first() if (free_selection is not None) else None
    )
    # Pre-resolve the title so templates never need to chain-traverse
    # free_selected_activity.activity.title (which can render as literal
    # text if attribute traversal unexpectedly fails in the template engine).
    free_selected_activity_title = (
        free_selected_activity.activity.title if free_selected_activity else ''
    )
    context = {
        'activities_data': activities_data,
        'categories': CATEGORY_CHOICES,
        'selected_category': category,
        'is_free_preview': not is_full_access,
        'free_selection': free_selection,
        'free_selected_activity': free_selected_activity,
        'free_selected_activity_title': free_selected_activity_title,
        'show_locked_modal': request.GET.get('locked') == '1',
        # Counted live so the headline cannot drift from the catalogue again —
        # it read "23" after the workshop activities were added back to the list.
        'total_activities': Activity.objects.filter(is_active=True).count(),
    }
    return render(request, 'activities/list.html', context)


@login_required
def activity_module_redirect(request, module):
    module = (module or '').strip().lower()
    activity = None

    # Try to find by category first
    activity = Activity.objects.filter(is_active=True, category=module).order_by('order').first()

    if not activity:
        if module == 'speaking':
            activity = Activity.objects.filter(
                is_active=True,
                title__icontains='Speaking',
            ).first()
        elif module == 'writing':
            activity = Activity.objects.filter(
                is_active=True,
                title__icontains='Writing',
            ).first()
        elif module == 'listening':
            activity = Activity.objects.filter(
                is_active=True,
                title__icontains='Listen',
            ).first()
        elif module == 'reading':
            activity = Activity.objects.filter(
                is_active=True,
                title__icontains='Reading',
            ).first()

    if activity:
        return redirect('activity_detail', pk=activity.pk)

    messages.warning(request, "That activity is not available yet.")
    return redirect('activity_list')



@login_required
def workshop_dashboard(request):
    """Dedicated dashboard for Interactive Workshop activities."""
    # Get activities from DB that are marked as workshop
    workshop_activities = Activity.objects.filter(category='workshop', is_active=True).order_by('order')

    workshop_modules = []
    for activity in workshop_activities:
        url = '#'
        title = activity.title.lower()
        if 'group discussion' in title: url = '/gd/'
        elif 'jam' in title: url = '/jam/'
        elif 'role play' in title: url = '/roleplay/'

        workshop_modules.append({
            'title': activity.title,
            'objective': activity.objective,
            'icon_class': activity.icon_class,
            'color_class': activity.color_class,
            'url': url,
            'level': activity.level
        })

    return render(request, 'activities/workshop_dashboard.html', {'workshop_modules': workshop_modules})



@login_required
def activity_detail(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    if not _can_access_activity(request.user, activity):
        return _locked_redirect()
    # Opening it spends the Free Plan user's single slot and locks the other four.
    _claim_free_activity(request.user, activity)

    # Workshop activities redirect to their dedicated apps
    if is_workshop_activity(activity):
        url = get_workshop_url(activity)
        if url:
            return redirect(url)

    # For the AI module types, skip the sub-activity layer and go straight to the exercise
    if is_module_activity(activity):
        ex = Exercise.objects.filter(sub_activity__activity=activity).order_by('sub_activity__order', 'order').first()
        if ex:
            return redirect('exercise_detail', exercise_pk=ex.pk)

    subactivities = activity.subactivities.prefetch_related('exercises')

    subactivities = list(subactivities)
    progress_map = {}
    pct_map = {}
    if request.user.is_authenticated:
        progress = UserProgress.objects.filter(user=request.user, sub_activity__activity=activity)
        progress_map = {p.sub_activity_id: p for p in progress}
        pct_map = perf.exercise_percentages(
            request.user, [e.id for s in subactivities for e in s.exercises.all()]
        )

    subs_with_status = []
    for sub in subactivities:
        prog = progress_map.get(sub.id)
        sub_perf = perf.sub_activity_progress(sub, pct_map)
        subs_with_status.append({
            'sub': sub,
            'progress': sub_perf,
            # Status comes from exercise results (Not started / In progress /
            # Completed = every exercise attempted); the percentage from scores.
            'status': sub_perf.status,
            'started_at': prog.started_at if prog else None,
            'completed_at': prog.completed_at if prog and sub_perf.status == 'completed' else None,
        })

    activity_perf = perf.summarize(
        [e.id for s in subactivities for e in s.exercises.all()], pct_map
    ) if request.user.is_authenticated else perf.EMPTY

    prev_activity = Activity.objects.filter(order__lt=activity.order).last()
    next_activity = Activity.objects.filter(order__gt=activity.order).first()

    context = {
        'activity': activity,
        'subs_with_status': subs_with_status,
        'activity_progress': activity_perf,
        'completion_rate': activity_perf.percent,
        'prev_activity': prev_activity,
        'next_activity': next_activity,
    }
    return render(request, 'activities/detail.html', context)



@login_required
def sub_activity_detail(request, activity_pk, sub_pk):
    activity = get_object_or_404(Activity, pk=activity_pk)
    sub = get_object_or_404(SubActivity, pk=sub_pk, activity=activity)
    if not _can_access_activity(request.user, activity):
        return _locked_redirect()
    # Opening it spends the Free Plan user's single slot and locks the other four.
    _claim_free_activity(request.user, activity)

    exercises = sub.exercises.prefetch_related('questions', 'bingo_cards')

    if request.user.is_authenticated:
        progress, _ = UserProgress.objects.get_or_create(user=request.user, sub_activity=sub)
        progress.mark_started()
    else:
        progress = None

    results_map = {}
    for exercise in exercises:
        result = UserExerciseResult.objects.filter(
            user=request.user, exercise=exercise
        ).order_by('-completed_at').first()
        results_map[exercise.id] = result

    prev_sub = SubActivity.objects.filter(activity=activity, order__lt=sub.order).last()
    next_sub = SubActivity.objects.filter(activity=activity, order__gt=sub.order).first()

    all_exercises_done = all(results_map.get(ex.id) for ex in exercises)
    sub_perf = perf.summarize(
        [ex.id for ex in exercises],
        perf.exercise_percentages(request.user, [ex.id for ex in exercises]),
    )

    context = {
        'activity': activity,
        'sub': sub,
        'exercises': exercises,
        'results_map': results_map,
        'progress': progress,
        'sub_progress': sub_perf,
        'all_exercises_done': all_exercises_done,
        'prev_sub': prev_sub,
        'next_sub': next_sub,
    }
    return render(request, 'activities/sub_activity.html', context)



@login_required
def exercise_detail(request, exercise_pk):
    exercise = get_object_or_404(Exercise, pk=exercise_pk)
    sub = exercise.sub_activity
    activity = sub.activity
    if not _can_access_activity(request.user, activity):
        return _locked_redirect()
    # Opening it spends the Free Plan user's single slot and locks the other four.
    _claim_free_activity(request.user, activity)

    # --- Route to specialised module template ---
    module_template = get_module_template(activity)

    if module_template:
        previous_result = None
        if request.user.is_authenticated:
            previous_result = UserExerciseResult.objects.filter(
                user=request.user, exercise=exercise
            ).order_by('-completed_at').first()
        # A fresh, unguessable token per page load. The listening module uses
        # this so a single attempt can only be evaluated once server-side —
        # loading/reloading the page mints a new token (a real "restart"),
        # while resubmitting without reloading reuses the same token and gets
        # rejected, even if the Submit button was re-enabled via devtools.
        import secrets
        attempt_token = secrets.token_hex(16)
        context = {
            'exercise': exercise,
            'sub': sub,
            'activity': activity,
            'previous_result': previous_result,
            'attempt_token': attempt_token,
            'previous_result_json': (
                json.dumps(previous_result.result_data)
                if previous_result and previous_result.result_data 
                else "null"
            ),
        }
        return render(request, module_template, context)

    # --- Default exercise flow (MCQ, Fill, etc.) ---
    questions = exercise.questions.all()
    bingo_cards = exercise.bingo_cards.all()

    previous_result = None
    all_attempts = []
    if request.user.is_authenticated:
        all_attempts = list(UserExerciseResult.objects.filter(
            user=request.user, exercise=exercise
        ).order_by('-completed_at'))
        if all_attempts:
            previous_result = all_attempts[0]

    context = {
        'exercise': exercise,
        'sub': sub,
        'activity': activity,
        'questions': questions,
        'bingo_cards': bingo_cards,
        'previous_result': previous_result,
        'all_attempts': all_attempts,
        'questions_json': json.dumps([
            {
                'id': q.id,
                'text': q.question_text,
                'type': exercise.exercise_type,
                'options': {
                    'a': q.option_a, 'b': q.option_b,
                    'c': q.option_c, 'd': q.option_d
                },
                'correct': q.correct_answer,
                'explanation': q.explanation,
                'left': q.left_item,
                'right': q.right_item,
            } for q in questions
        ]),
        'bingo_json': json.dumps(
            [{'word': b.word, 'definition': b.definition} for b in bingo_cards]
        ),
    }
    return render(request, 'activities/exercise.html', context)


@login_required
@require_POST
def submit_exercise(request, exercise_pk):
    exercise = get_object_or_404(Exercise, pk=exercise_pk)
    data = json.loads(request.body)
    score = data.get('score', 0)
    max_score = data.get('max_score', 0)
    answers = data.get('answers', {})

    custom_summary_html = ""

    if exercise.exercise_type in ('writing', 'timer') and settings.SARVAM_API_KEY:
        from activities.agents.utils import analyze_text_with_sarvam_chat
        import logging
        logger = logging.getLogger(__name__)

        total_q_score = 0
        ai_feedbacks = []
        questions = list(exercise.questions.all().order_by('id'))

        # Timer exercises contain spoken transcripts; use the speaking analysis
        # mode so the AI evaluates fluency/delivery rather than written prose.
        ai_mode = "speaking" if exercise.exercise_type == "timer" else "writing"
        
        for i, q in enumerate(questions):
            ans = answers.get(str(i+1), "")
            word_count = len(ans.split())
            # Spoken transcripts can be shorter than written essays; any distinct
            # speech is worth evaluating for practice mode.
            min_words = 0 if exercise.exercise_type == "timer" else 10
            if word_count > min_words:
                try:
                    res = analyze_text_with_sarvam_chat(ai_mode, ans, q.question_text, 0, 0, settings.SARVAM_API_KEY)
                    scores = res.get('scores', {})
                    overall = scores.get('overall', 0)
                    relevance = scores.get('relevance', 100) # Default to 100 if missing
                    
                    # Hard penalty for low relevance (skip for timer to always generate a score)
                    if relevance < 50 and exercise.exercise_type != "timer":
                        overall = min(overall, relevance)
                        
                    # Apply safety checks (repetition and prompt copying)
                    from activities.agents.utils import repetition_ratio, compute_reference_similarity, clamp_score
                    rep_ratio = repetition_ratio(ans)
                    if rep_ratio >= 0.34:
                        capped = clamp_score(round(40 * (1 - rep_ratio)), 5)
                        overall = min(overall, capped)
                        
                    similarity = compute_reference_similarity(q.question_text, ans)
                    if similarity > 0.65:
                        overall = min(overall, 10)
                        
                    total_q_score += overall

                    if exercise.exercise_type != "timer":
                        q_html = f"<div class='mt-3 mb-2 text-start'><strong>Task {i+1}:</strong></div>"
                        
                        issues = res.get('issues', [])
                        if issues:
                            q_html += "<ul class='text-start ps-4' style='font-size: 0.9em;'>"
                            for issue in issues:
                                q_html += f"<li class='mb-2'><strong><span class='text-danger'>{issue.get('phrase', '')}</span></strong>: {issue.get('message', '')} <br><span class='text-success'>Suggestion: {issue.get('suggestion', '')}</span></li>"
                            q_html += "</ul>"
                        else:
                            q_html += "<div class='text-success text-start mb-2 ps-2'><i class='fas fa-check-circle me-1'></i>No major issues found.</div>"
                        
                        improved = res.get('improved_passage', '')
                        if improved:
                            q_html += f"<div class='p-3 bg-light border rounded text-start mt-2' style='font-size: 0.9em; white-space: pre-wrap;'><strong>Improved Version:</strong><br>{improved}</div>"
                        
                        ai_feedbacks.append(q_html)
                except Exception as e:
                    logger.error(f"AI evaluation failed for exercise {exercise_pk}: {e}")
                    total_q_score += score / (len(questions) or 1)
            else:
                total_q_score += 0
                if exercise.exercise_type != "timer":
                    ai_feedbacks.append(f"<div class='mt-3 mb-2 text-danger text-start'><strong>Task {i+1}:</strong> Answer too short to evaluate.</div>")
        
        if questions:
            score = round(total_q_score / len(questions))
        else:
            score = 0
        max_score = 100
        custom_summary_html = "".join(ai_feedbacks)

    else:
        # Everything not scored by the AI above is checked on the server:
        # progress is built from these scores, so the browser's own number is
        # never taken on trust (see activities/grading.py).
        score, max_score = grade_submission(exercise, score, max_score, answers)

    attempt = UserExerciseResult.objects.filter(
        user=request.user, exercise=exercise
    ).count() + 1

    result = UserExerciseResult.objects.create(
        user=request.user,
        exercise=exercise,
        score=score,
        max_score=max_score,
        answers_json=answers,
        attempt_number=attempt,
    )

    if exercise.sub_activity:
        progress, _ = UserProgress.objects.get_or_create(user=request.user, sub_activity=exercise.sub_activity)
        # Only the last of several exercises in a sub-activity should flip it
        # to 'completed' — one submission out of many must leave it 'in_progress'.
        if exercise.sub_activity.all_exercises_done(request.user):
            progress.mark_completed()
        else:
            progress.mark_started()

    # Updated progress, so the result panel can show it straight away.
    sub_progress = activity_progress = None
    if exercise.sub_activity:
        sub_progress = perf.progress_for_sub_activity(request.user, exercise.sub_activity).as_dict()
        activity_progress = perf.progress_for_activity(
            request.user, exercise.sub_activity.activity
        ).as_dict()

    return JsonResponse({
        'status': 'ok',
        'score': score,
        'max_score': max_score,
        'percentage': result.percentage,
        'attempt': attempt,
        'customSummaryHtml': custom_summary_html,
        'sub_progress': sub_progress,
        'activity_progress': activity_progress,
    })


@login_required
@require_POST
def delete_attempt(request, attempt_pk):
    """Delete one of the current user's own exercise attempts.

    Scoped to `user=request.user` so a user can only ever delete their own
    attempts — never another user's — even by guessing an id.
    """
    attempt = get_object_or_404(UserExerciseResult, pk=attempt_pk, user=request.user)
    exercise_pk = attempt.exercise_id
    attempt.delete()
    messages.success(request, "Attempt deleted.")
    return redirect('exercise_detail', exercise_pk=exercise_pk)


@login_required
@require_POST
def mark_sub_complete(request, sub_pk):
    sub = get_object_or_404(SubActivity, pk=sub_pk)
    progress, _ = UserProgress.objects.get_or_create(user=request.user, sub_activity=sub)
    progress.mark_completed()
    messages.success(request, f'"{sub.title}" marked as completed!')
    return redirect('sub_activity_detail', activity_pk=sub.activity_id, sub_pk=sub.id)


# --------------------------------------------------------------------------- #
#  AI Module Analyze endpoints
# --------------------------------------------------------------------------- #

def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _normalised_module_score(scores, *keys, default=70):
    """FR-AIM-05: round(raw x 25 / 100) clamped to 0-25.

    Reads the first of `keys` that holds a real number (bools and non-numeric
    provider values are ignored), falling back to `default`.
    """
    scores = scores or {}
    value = None
    for key in keys:
        candidate = scores.get(key)
        if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
            value = candidate
            break
    if value is None:
        value = default
    try:
        return max(0, min(25, round(float(value) * 25 / 100)))
    except (TypeError, ValueError):
        return max(0, min(25, round(default * 25 / 100)))


def _module_access_denied(request, exercise):
    """403 JsonResponse if the user's plan cannot consume this exercise, else None.

    A Free Plan user must not spend paid AI analysis on a locked activity.
    """
    activity = getattr(exercise.sub_activity, 'activity', None) if exercise.sub_activity else None
    if activity and not _can_access_activity(request.user, activity):
        return JsonResponse(
            {'success': False, 'data': {}, 'error': 'This activity requires an upgrade to access.'},
            status=403,
        )
    return None


def _save_module_result(user, exercise, score_out_of_25, result_data=None):
    """Save AI module result into UserExerciseResult (score out of 25)."""
    attempt = UserExerciseResult.objects.filter(user=user, exercise=exercise).count() + 1
    UserExerciseResult.objects.create(
        user=user,
        exercise=exercise,
        score=score_out_of_25,
        max_score=25,
        answers_json={'module_result': True},
        result_data=result_data,
        attempt_number=attempt,
    )
    if exercise.sub_activity:
        progress, _ = UserProgress.objects.get_or_create(user=user, sub_activity=exercise.sub_activity)
        # Only flip to 'completed' once every exercise in the sub-activity has
        # a result — matches the same rule in submit_exercise().
        if exercise.sub_activity.all_exercises_done(user):
            progress.mark_completed()
        else:
            progress.mark_started()


@login_required
@require_POST
def analyze_speaking(request, exercise_pk):
    """Receive audio + metadata, run SpeakingAgent, return JSON feedback."""
    exercise = get_object_or_404(Exercise, pk=exercise_pk)

    denied = _module_access_denied(request, exercise)
    if denied:
        return denied

    from .agents.speaking import SpeakingAgent
    agent = SpeakingAgent()

    payload = {
        'audio': request.FILES.get('audio'),
        'client_transcript': request.POST.get('client_transcript', ''),
        'reference_text': request.POST.get('reference_text', ''),
        'duration_seconds': _safe_float(request.POST.get('duration_seconds', 0)),
        'pause_count': _safe_int(request.POST.get('pause_count', 0)),
        'language': request.POST.get('language', 'english'),
    }

    result = agent.safe_run(payload)

    if result.get('success') and request.user.is_authenticated:
        data = result.get('data')
        if isinstance(data, dict):
            scores = data.get('scores', {})
            score_25 = _normalised_module_score(
                scores,
                'overall',
                'fluency'
            )

            # Cap score if relevance is low
            relevance = scores.get('relevance')
            if isinstance(relevance, (int, float)) and not isinstance(relevance, bool):
                if relevance < 50:
                    score_25 = min(score_25, 10)

            _save_module_result(
                request.user,
                exercise,
                score_25,
                result_data=data
            )

            result['score_25'] = score_25  # type: ignore[index]

            # Inject a convenient top-level transcript key
            data['transcript'] = data.get('text', '')
            # Store the authoritative score_25 inside result_data so the JS can
            # read it back verbatim when showing a previous result on page reload,
            # rather than re-deriving it from raw scores with possible rounding drift.
            data['score_25'] = score_25

    return JsonResponse(result)


@login_required
@require_POST
def analyze_writing(request, exercise_pk):
    """Receive text (FormData or JSON), run WritingAgent, return JSON feedback."""
    exercise = get_object_or_404(Exercise, pk=exercise_pk)

    denied = _module_access_denied(request, exercise)
    if denied:
        return denied

    # Writing JS sends FormData; fallback to JSON body
    text = request.POST.get('text', '')
    language = request.POST.get('language', 'english')
    if not text:
        try:
            body = json.loads(request.body)
            text = body.get('text', '')
            language = body.get('language', 'english')
        except Exception:
            pass
    # Proposal and Bid Writing -> Proposal Section Writing
    # requires 150-200 words.
    word_count = len(re.findall(r"\b[\w'-]+\b", text))

    is_proposal_section_writing = (
        str(getattr(exercise, "title", "")).strip().lower()
        == "proposal section writing"
        and str(
            getattr(getattr(exercise, "sub_activity", None), "activity", None)
            and getattr(exercise.sub_activity.activity, "title", "")
        ).strip().lower()
        == "proposal and bid writing"
    )

    if is_proposal_section_writing and not (150 <= word_count <= 200):
        return JsonResponse({
            "success": False,
            "error": (
                f"Your response must contain between 150 and 200 words. "
                f"You entered {word_count} words."
            ),
            "word_count": word_count,
            "min_words": 150,
            "max_words": 200,
        }, status=400)

    from .agents.writing import WritingAgent
    agent = WritingAgent()

    payload = {
        'text': text,
        'reference_text': request.POST.get('reference_text', ''),
        'language': language,
    }

    result = agent.safe_run(payload)

    if result['success'] and request.user.is_authenticated:
        scores = result['data'].get('scores', {})
        score_25 = _normalised_module_score(
            scores,
            'overall',
            'grammar'
        )
        
        # Cap score if relevance is low
        relevance = scores.get('relevance')
        if isinstance(relevance, (int, float)) and not isinstance(relevance, bool):
            if relevance < 50:
                score_25 = min(score_25, 10)

        _save_module_result(
            request.user,
            exercise,
            score_25,
            result_data=result['data']
        )

        result['score_25'] = score_25  # type: ignore[index]

    return JsonResponse(result)


@login_required
@require_POST
def analyze_listening(request, exercise_pk):
    """Receive typed transcript + reference (FormData or JSON), run ListeningAgent, return JSON."""
    exercise = get_object_or_404(Exercise, pk=exercise_pk)

    denied = _module_access_denied(request, exercise)
    if denied:
        return denied

    # listening.js sends FormData
    text = request.POST.get('text', '')
    reference_text = request.POST.get('reference_text', '')
    language = request.POST.get('language', 'english')
    duration_seconds = _safe_float(request.POST.get('duration_seconds', 0))
    pause_count = _safe_int(request.POST.get('pause_count', 0))
    attempt_token = request.POST.get('attempt_token', '')
    if not text:
        try:
            body = json.loads(request.body)
            text = body.get('text', '')
            reference_text = body.get('reference_text', '')
            language = body.get('language', 'english')
            duration_seconds = _safe_float(body.get('duration_seconds', 0))
            pause_count = _safe_int(body.get('pause_count', 0))
            attempt_token = body.get('attempt_token', attempt_token)
        except Exception:
            pass

    # Each page load mints a fresh attempt_token (see exercise_detail). The UI
    # disables the form after a successful evaluation, but that's only a
    # convenience — a user can re-enable a disabled button via devtools and
    # POST again with a different or copied answer. Enforce "one evaluation
    # per attempt" here too: reject a request whose token has already been
    # used, or that has no token at all. Refreshing/restarting the activity
    # gets a new token and is allowed to evaluate again.
    used_tokens_key = f'listening_used_tokens_{exercise.pk}'
    used_tokens = request.session.get(used_tokens_key, [])
    if not attempt_token:
        return JsonResponse({
            'success': False,
            'data': {},
            'error': 'Could not verify this attempt. Please refresh the activity and try again.',
        }, status=409)
    if attempt_token in used_tokens:
        return JsonResponse({
            'success': False,
            'data': {},
            'error': 'This attempt has already been evaluated. Restart or refresh the activity to try again.',
        }, status=409)

    from .agents.listening import ListeningAgent
    agent = ListeningAgent()

    payload = {
        'text': text,
        'reference_text': reference_text,
        'duration_seconds': duration_seconds,
        'pause_count': pause_count,
        'language': language,
    }


    result = agent.safe_run(payload)

    if result['success'] and request.user.is_authenticated:
        data = result.get('data')
        if isinstance(data, dict):
            from .agents.utils import compute_listening_score_25, compute_reference_similarity

            # Anti-cheat: once a learner analyzes an attempt, the UI reveals a
            # corrected "Improved Version" of their summary — genuinely useful
            # for learning, but if that exact revealed text comes back as the
            # "understanding" on a *later* attempt at the same exercise, that
            # isn't comprehension, it's pasting the answer key we just showed
            # them back at us. We remember what was last revealed for this
            # exercise in the session and zero out a submission that's really
            # just a copy of it, instead of letting it score as a near-perfect
            # content match.
            reveal_session_key = f'listening_last_reveal_{exercise.pk}'
            previously_revealed = request.session.get(reveal_session_key, '')
            copied_from_reveal = bool(previously_revealed) and compute_reference_similarity(previously_revealed, text) >= 0.92

            if copied_from_reveal:
                score_25, content_match_percent = 0, 0
                data['feedback'] = (
                    "This looks copied from the corrected version shown on your previous attempt, "
                    "not written in your own words. Please listen again and write your own understanding "
                    "of the story to get a real score."
                )
            else:
                # The AI's 'scores' dict grades generic language quality
                # (fluency/grammar/spelling) and is not a reliable signal of
                # whether the summary actually matches what the story was
                # about (it can be a perfect 100 on an unrelated summary) —
                # and its key names vary run to run. Score this "what did you
                # understand" exercise from actual content similarity against
                # the story instead, so Total Score always agrees with the
                # Content Match % shown right next to it.
                issues = data.get('issues')
                issues_list: list = issues if isinstance(issues, list) else []
                score_25, content_match_percent = compute_listening_score_25(
                    reference_text, text, pause_count, len(issues_list)
                )

            # Cap score if relevance is low
            relevance = data.get('scores', {}).get('relevance')
            if isinstance(relevance, (int, float)) and not isinstance(relevance, bool):
                if relevance < 50:
                    score_25 = min(score_25, 10)

            _save_module_result(
              request.user,
              exercise,
              score_25,
              result_data=data
            )
            # Send the exact score that was just saved back to the frontend, so
            # the score shown right after analysis ("Present") is guaranteed to
            # match what UserExerciseResult now holds and later displays as
            # "Previous". Also send the match % it was derived from, so Total
            # Score and Content Match always agree instead of coming from two
            # independent calculations.
            data['score_25'] = score_25
            data['content_match_percent'] = content_match_percent

            # Remember what's about to be revealed on screen this time (the
            # improved/corrected passage), so a follow-up attempt that just
            # copies it back can be caught.
            if data.get('improved_passage'):
                request.session[reveal_session_key] = data['improved_passage']

            # Mark this attempt as spent so a resubmission with the same
            # token (i.e. without an actual page restart/refresh) is
            # rejected up front, before it ever reaches the AI or the score
            # calculation above. Cap the stored list so the session can't
            # grow unbounded over a very long history of attempts.
            used_tokens.append(attempt_token)
            request.session[used_tokens_key] = used_tokens[-20:]

    return JsonResponse(result)


@login_required
@require_POST
def analyze_reading(request, exercise_pk):
    """Receive audio/text + passage, run ReadingAgent, return JSON feedback."""
    exercise = get_object_or_404(Exercise, pk=exercise_pk)

    denied = _module_access_denied(request, exercise)
    if denied:
        return denied

    from .agents.reading import ReadingAgent
    agent = ReadingAgent()

    payload = {
        'audio': request.FILES.get('audio'),
        'text': request.POST.get('text', ''),
        'client_transcript': request.POST.get('client_transcript', ''),
        'reference_text': request.POST.get('reference_text', ''),
        'duration_seconds': _safe_float(request.POST.get('duration_seconds', 0)),
        'pause_count': _safe_int(request.POST.get('pause_count', 0)),
        'language': request.POST.get('language', 'english'),
    }

    result = agent.safe_run(payload)

    if result['success'] and request.user.is_authenticated:
        data = result.get('data')

        if isinstance(data, dict):
            scores = data.get('scores', {})

            # Use the actual reading accuracy/pronunciation score.
            score_25 = _normalised_module_score(
                scores,
                'overall',
                'accuracy',
                'pronunciation'
            )

            # Cap score if relevance is low
            relevance = scores.get('relevance')
            if isinstance(relevance, (int, float)) and not isinstance(relevance, bool):
                if relevance < 50:
                    score_25 = min(score_25, 10)

            _save_module_result(
                request.user,
                exercise,
                score_25,
                result_data=data
            )

            data['score_25'] = score_25  # type: ignore[index]
            result['score_25'] = score_25  # type: ignore[index]

    return JsonResponse(result)


# ---------------------------------------------------------------------------
# Roleplay Module Views
# ---------------------------------------------------------------------------

@login_required
def roleplay_home(request):
    """
    Landing page for the Roleplay module.
    Allows selection between Storytelling, Situations, and Roleplay.
    """
    if not _can_access_workshop(request.user, 'roleplay'):
        return _locked_redirect()
    from riya_bot.agents.utils import TOPIC_PRACTICE_CONFIG

    return render(request, 'activities/modules/roleplay_home.html', {
        'configs': TOPIC_PRACTICE_CONFIG
    })


@login_required
def roleplay_practice_view(request, feature):
    """Specific practice page for a feature (storytelling, situations, or roleplay)."""

    if not _can_access_workshop(request.user, 'roleplay'):
        return _locked_redirect()

    from riya_bot.agents.utils import get_topic_practice_config
    config = get_topic_practice_config(feature)
    if not config:
        return redirect('roleplay_home')

    return render(request, 'activities/modules/roleplay.html', {
        'active_topic': feature,
        'topic_config': config,
    })


# A roleplay scene needs two people in it — "Student and Teacher",
# "Customer and Shopkeeper" — not a single subject/character like
# "Environment" or "Manager". This is a heuristic, not real NLP: a short
# prompt (<=3 words) must name a second party via a connector word; a
# longer prompt is assumed to already describe an interaction (e.g. the
# shipped example "Customer asking for a refund" implies a second party
# without ever using the word "and").
_ROLEPLAY_TWO_PARTY_CONNECTOR = re.compile(r'\b(and|vs\.?|versus|with)\b|&|,', re.IGNORECASE)


def _roleplay_prompt_missing_second_character(prompt):
    text = (prompt or '').strip()
    if not text:
        return False  # empty prompt falls back to config['default_prompt'], which is fine
    if len(text.split()) > 3:
        return False
    return not _ROLEPLAY_TWO_PARTY_CONNECTOR.search(text)


@login_required
@require_POST
def roleplay_practice(request):
    """API endpoint for generating content using Sarvam AI or fallback."""
    if not _can_access_workshop(request.user, 'roleplay'):
        return JsonResponse(
            {
                'success': False,
                'error': 'This activity is locked for your current plan.'
            },
            status=403
        )
    from riya_bot.agents.utils import (
        get_topic_practice_config,
        fallback_topic_practice,
        topic_practice_with_sarvam_chat
    )

    topic_slug = request.POST.get('topic', 'roleplay')
    prompt = request.POST.get('prompt', '').strip()
    language = request.POST.get('language', 'english')

    config = get_topic_practice_config(topic_slug)
    if not config:
        return JsonResponse({"error": f"Unknown topic: '{topic_slug}'"}, status=400)

    # Only the Roleplay feature needs two named characters — Storytelling and
    # Situations are single-narrator/single-scene modes and don't apply here.
    if config.get('slug') == 'roleplay' and _roleplay_prompt_missing_second_character(prompt):
        return JsonResponse(
            {"error": "Please provide another character to start the roleplay."},
            status=400,
        )

    from django.conf import settings
    api_key = getattr(settings, 'SARVAM_API_KEY', '')

    result = {}
    if api_key:
        try:
            result = topic_practice_with_sarvam_chat(config, prompt, api_key, language) or {}
        except Exception:
            result = {}

    if not result:
        result = fallback_topic_practice(config, prompt)

    used_prompt = prompt or config.get('default_prompt', '')
    return JsonResponse({
        "topic": topic_slug,
        "used_prompt": used_prompt,
        "result": result
    })


@login_required
def analyze_roleplay(request):
    """Analyze a roleplay session audio and transcript."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    from .agents.speaking import SpeakingAgent
    agent = SpeakingAgent()

    payload = {
        'audio': request.FILES.get('audio'),
        'client_transcript': request.POST.get('client_transcript', ''),
        'reference_text': request.POST.get('reference_text', ''),
        'duration_seconds': _safe_float(request.POST.get('duration_seconds', 0)),
        'pause_count': _safe_int(request.POST.get('pause_count', 0)),
        'language': request.POST.get('language', 'english'),
    }

    result = agent.safe_run(payload)

    if result['success']:
        # Save to ScoreRecord for the dashboard
        from core.models import ScoreRecord
        data = result['data']
        scores = data.get('scores', {})
        score_25 = _normalised_module_score(scores, 'overall', 'fluency')
        
        # Cap score if relevance is low
        relevance = scores.get('relevance')
        if isinstance(relevance, (int, float)) and not isinstance(relevance, bool):
            if relevance < 50:
                score_25 = min(score_25, 10)

        ScoreRecord.objects.create(
            user=request.user,
            module='roleplay',
            score=score_25,
            max_score=25,
            label=f"Roleplay: {request.POST.get('topic', 'Practice')}"
        )

    return JsonResponse(result)

# --------------------------------------------------------------------------- #
#  OOP Mastery quiz — server-side question bank (answers never sent to client
#  until after submission; a random 50 of 300 is served per attempt).
# --------------------------------------------------------------------------- #
import random as _random
from pathlib import Path as _Path

_OOP_QUESTIONS = None


# --------------------------------------------------------------------------- #
#  Option rotation + grading, shared by every mock test (subject quizzes, AMCAT,
#  CoCubes, the legacy OOP quiz).
#
#  The question banks are heavily biased: oop had the correct answer at option A
#  in 289 of 300 questions, tensorflow at B in 290 of 300, blockchain at B in
#  285 of 300. A candidate who always picks the same letter passed. Options are
#  therefore rotated per question before they are sent, and the submitted index
#  is mapped back before grading — no change to the 27 bank files.
#
#  The rotation is derived from the question id plus the user id, so the server
#  recomputes the same order at submit time without storing anything, and two
#  candidates sitting the same test see different arrangements.
# --------------------------------------------------------------------------- #

def _quiz_salt(request, create=False):
    """Seed the option rotation is derived from.

    The user id, so two candidates see different arrangements, and nothing
    else: it must produce the SAME rotation at submit time as at fetch time.
    A per-attempt salt in the session would do that too until the session is
    missing on submit (blocked cookies, expiry), and then every answer would
    be mapped against the wrong order and graded wrong. `create` is accepted
    so the fetch and submit call sites read alike.
    """
    user = getattr(request, 'user', None)
    return f'u{user.pk}' if getattr(user, 'is_authenticated', False) else ''


def _option_order(qid, options, salt):
    """Display order for one question: a list of indexes into `options`."""
    order = list(range(len(options)))
    _random.Random(f'{salt}:{qid}').shuffle(order)
    return order


def _serve_options(q, salt):
    """The question's options in rotated display order."""
    options = q.get('options') or []
    return [options[i] for i in _option_order(q['id'], options, salt)]


def _grade_choice(q, chosen, salt):
    """(attempted, is_correct, correct_display_index) for one submitted answer.

    Grading compares the TEXT of the chosen option with the text of the correct
    one, not the index: some questions ship the same option twice (25 in
    cocubes_full, 3 in english), and picking the duplicate of the right answer
    must not be marked wrong.
    """
    options = q.get('options') or []
    order = _option_order(q['id'], options, salt)
    correct_index = q.get('answer')
    correct_display = order.index(correct_index) if correct_index in order else -1
    attempted = isinstance(chosen, int) and 0 <= chosen < len(order)
    if not attempted:
        return False, False, correct_display
    picked = options[order[chosen]]
    is_correct = picked == options[correct_index] if 0 <= correct_index < len(options) else False
    return True, is_correct, correct_display


# Spreadsheet error strings that leaked into the banks when the questions were
# exported (english 579/609/632 carry '#NAME?' as an option).
_BROKEN_OPTIONS = {'#NAME?', '#REF!', '#VALUE!', '#N/A', ''}


def _usable_questions(pool):
    """Questions that can actually be answered as written.

    Drops two kinds of broken question: options that repeat (25 in
    cocubes_full, 3 in english — the candidate is asked to choose between two
    identical choices) and options that are spreadsheet error text left over
    from the export. Logged per bank, never dropped silently.
    """
    good = []
    for q in pool:
        options = [str(o).strip() for o in (q.get('options') or [])]
        if not options or len(options) != len(set(options)):
            continue
        if any(o in _BROKEN_OPTIONS for o in options):
            continue
        good.append(q)
    dropped = len(pool) - len(good)
    if dropped:
        logger.warning('Question bank: skipped %s unusable question(s) '
                       '(duplicate or broken options)', dropped)
    return good


def _load_oop_questions():
    global _OOP_QUESTIONS
    if _OOP_QUESTIONS is None:
        p = _Path(__file__).resolve().parent / 'data' / 'oop_questions.json'
        with open(p, encoding='utf-8') as fh:
            _OOP_QUESTIONS = json.load(fh)
    return _OOP_QUESTIONS


@require_GET
def oop_quiz_questions(request):
    """Return a random 50 of the 300 OOP questions, WITHOUT the answers."""
    pool = _usable_questions(_load_oop_questions())
    pick = _random.sample(pool, min(50, len(pool)))
    salt = _quiz_salt(request, create=True)
    payload = [
        {"id": q["id"], "q": q["q"], "options": _serve_options(q, salt),
         "difficulty": q["difficulty"], "topic": q["topic"]}
        for q in pick
    ]
    return JsonResponse({"questions": payload})


@csrf_exempt
@require_POST
def oop_quiz_submit(request):
    """Grade a submission server-side. Body: {"answers": {id: chosenIndex}}."""
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({"error": "invalid payload"}, status=400)
    answers = data.get("answers", {}) or {}
    by_id = {q["id"]: q for q in _load_oop_questions()}
    salt = _quiz_salt(request)
    results, score, total = {}, 0, 0
    for qid, chosen in answers.items():
        try:
            qid = int(qid)
        except (ValueError, TypeError):
            continue
        q = by_id.get(qid)
        if not q:
            continue
        total += 1
        # Only reveal the correct answer/explanation for questions the user
        # actually attempted. Unanswered (sentinel like -1) reveals nothing —
        # stops blank-submit harvesting. `answer` is the index in the order the
        # options were SHOWN, which is what the page highlights.
        attempted, is_correct, correct_display = _grade_choice(q, chosen, salt)
        if is_correct:
            score += 1
        res = {"correct": is_correct}
        if attempted:
            res["answer"] = correct_display
            res["explanation"] = q["explanation"]
        results[qid] = res
    from skillup_assessment.services import after_grading
    return JsonResponse({"score": score, "total": total, "results": results,
                         **after_grading(request.user, 'oop', score, total)})


# --------------------------------------------------------------------------- #
#  Generic subject quiz (Python, DSA, …) — same protection model as OOP:
#  random 50/300, answers graded server-side, revealed only for attempted Qs.
# --------------------------------------------------------------------------- #
_BANKS = {}
_QUIZ_SUBJECTS = {
    'oop', 'python', 'dsa', 'devops', 'claude', 'uiux', 'design', 'vector',
    'nltk', 'dbms', 'prompt', 'genai', 'crewai', 'english', 'aptitude',
    'quantum', 'vr', 'robotics', 'nodejs', 'mlops', 'ethical',
    'tensorflow', 'cyber', 'blockchain', 'crypto',
}


def _load_bank(name):
    if name not in _BANKS:
        p = _Path(__file__).resolve().parent / 'data' / (name + '_questions.json')
        with open(p, encoding='utf-8') as fh:
            _BANKS[name] = json.load(fh)
    return _BANKS[name]


@require_GET
def quiz_questions(request, subject):
    if subject not in _QUIZ_SUBJECTS:
        return JsonResponse({"error": "unknown subject"}, status=404)
    pool = _usable_questions(_load_bank(subject))
    pick = _random.sample(pool, min(50, len(pool)))
    salt = _quiz_salt(request, create=True)
    payload = [
        {"id": q["id"], "q": q["q"], "options": _serve_options(q, salt),
         "difficulty": q.get("difficulty", ""), "topic": q.get("topic", "")}
        for q in pick
    ]
    return JsonResponse({"questions": payload})


@csrf_exempt
@require_POST
def quiz_submit(request, subject):
    if subject not in _QUIZ_SUBJECTS:
        return JsonResponse({"error": "unknown subject"}, status=404)
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({"error": "invalid payload"}, status=400)
    answers = data.get("answers", {}) or {}
    by_id = {q["id"]: q for q in _load_bank(subject)}
    salt = _quiz_salt(request)
    results, score, total = {}, 0, 0
    for qid, chosen in answers.items():
        try:
            qid = int(qid)
        except (ValueError, TypeError):
            continue
        q = by_id.get(qid)
        if not q:
            continue
        total += 1
        attempted, is_correct, correct_display = _grade_choice(q, chosen, salt)
        if is_correct:
            score += 1
        res = {"correct": is_correct}
        if attempted:
            res["answer"] = correct_display
            res["explanation"] = q["explanation"]
        results[qid] = res
    # Same bookkeeping as the AMCAT/CoCubes endpoints: record the attempt AND
    # generate the certificate when it is earned. Previously this endpoint only
    # saved the attempt, so a subject quiz never issued a certificate at submit
    # time — it appeared only after the candidate happened to open the
    # certificate page.
    from skillup_assessment.services import after_grading
    return JsonResponse({"score": score, "total": total, "results": results,
                         **after_grading(request.user, subject, score, total)})


# -- AMCAT full mock: 5 modules, random questions per module (answers server-side) --
_AMCAT_PLAN = [
    ("quant", "Quantitative Ability", 16, 18 * 60),
    ("english", "English Ability", 18, 16 * 60),
    ("logical", "Logical Reasoning", 14, 16 * 60),
    ("personality", "AMCAT Personality Inventory", 90, 20 * 60),
    ("domain", "Domain Module — Computer Programming", 15, 15 * 60),
]
_AMCAT_BANK = None


def _amcat_bank():
    global _AMCAT_BANK
    if _AMCAT_BANK is None:
        p = _Path(__file__).resolve().parent / 'data' / 'amcat_full.json'
        with open(p, encoding='utf-8') as fh:
            data = json.load(fh)
        grouped = {}
        for q in data:
            grouped.setdefault(q["section"], []).append(q)
        _AMCAT_BANK = grouped
    return _AMCAT_BANK


@require_GET
def amcat_questions(request):
    bank = _amcat_bank()
    sections = []
    salt = _quiz_salt(request, create=True)
    for key, name, count, secs in _AMCAT_PLAN:
        pool = _usable_questions(bank.get(key, []))
        pick = _random.sample(pool, min(count, len(pool)))
        sections.append({
            "key": key, "name": name, "timeSec": secs, "type": "mcq",
            "questions": [{"id": q["id"], "q": q["q"], "options": _serve_options(q, salt)}
                          for q in pick],
        })
    return JsonResponse({"sections": sections})


@csrf_exempt
@require_POST
def amcat_submit(request):
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({"error": "invalid payload"}, status=400)
    answers = data.get("answers", {}) if isinstance(data, dict) else {}
    if not isinstance(answers, dict):
        return JsonResponse({"error": "invalid payload"}, status=400)
    by_id = {q["id"]: q for pool in _amcat_bank().values() for q in pool}
    salt = _quiz_salt(request)
    results = {}
    sec_score = {k: {"name": n, "correct": 0, "total": 0}
                 for k, n, _c, _t in _AMCAT_PLAN}
    score = total = 0
    for qid, chosen in answers.items():
        try:
            qid = int(qid)
        except (ValueError, TypeError):
            continue
        q = by_id.get(qid)
        if not q:
            continue
        if q["section"] not in sec_score:
            continue
        total += 1
        sec_score[q["section"]]["total"] += 1
        attempted, is_correct, correct_display = _grade_choice(q, chosen, salt)
        if is_correct:
            score += 1
            sec_score[q["section"]]["correct"] += 1
        res = {"correct": is_correct, "section": q["section"]}
        if attempted:
            res["answer"] = correct_display
            res["explanation"] = q["explanation"]
        results[qid] = res
    # Saving the attempt and the certificate are isolated from grading: the
    # score above is final, so a failure there is logged and flagged, never
    # turned into a "Could not grade the test" error on the page.
    from skillup_assessment.services import after_grading
    return JsonResponse({"score": score, "total": total,
                         "percentage": (score * 100 // total) if total else 0,   # rounded down, like the 70% rule
                         "sections": sec_score, "results": results,
                         **after_grading(request.user, 'amcat', score, total)})


# -- CoCubes full mock: 4 sections (3 MCQ graded + Programming free-text, ungraded) --
_COCUBES_PLAN = [
    ("aptitude", "Aptitude", "mcq", 50, 50 * 60),
    ("technical", "Technical / Domain (CSE-IT)", "mcq", 25, 25 * 60),
    ("compfun", "Computer Fundamentals", "mcq", 25, 25 * 60),
    ("programming", "Programming", "mcq", 50, 50 * 60),
]
_COCUBES_BANK = None


def _cocubes_bank():
    global _COCUBES_BANK
    if _COCUBES_BANK is None:
        p = _Path(__file__).resolve().parent / 'data' / 'cocubes_full.json'
        with open(p, encoding='utf-8') as fh:
            data = json.load(fh)
        grouped = {}
        for q in data:
            grouped.setdefault(q["section"], []).append(q)
        _COCUBES_BANK = grouped
    return _COCUBES_BANK


@require_GET
def cocubes_questions(request):
    bank = _cocubes_bank()
    sections = []
    salt = _quiz_salt(request, create=True)
    for key, name, typ, count, secs in _COCUBES_PLAN:
        pool = bank.get(key, [])
        if typ != "code":
            pool = _usable_questions(pool)
        pick = _random.sample(pool, min(count, len(pool)))
        if typ == "code":
            qs = [{"id": q["id"], "title": q.get("title", ""), "q": q["q"],
                   "example": q.get("example", "")} for q in pick]
        else:
            qs = [{"id": q["id"], "q": q["q"], "options": _serve_options(q, salt)} for q in pick]
        sections.append({"key": key, "name": name, "type": typ,
                         "timeSec": secs, "questions": qs})
    return JsonResponse({"sections": sections})


@csrf_exempt
@require_POST
def cocubes_submit(request):
    try:
        data = json.loads(request.body or b'{}')
    except (ValueError, TypeError):
        return JsonResponse({"error": "invalid payload"}, status=400)
    answers = data.get("answers", {}) if isinstance(data, dict) else {}
    if not isinstance(answers, dict):
        return JsonResponse({"error": "invalid payload"}, status=400)
    by_id = {q["id"]: q for pool in _cocubes_bank().values() for q in pool}
    salt = _quiz_salt(request)
    results = {}
    sec_score = {k: {"name": n, "type": t, "correct": 0, "total": 0}
                 for k, n, t, _c, _s in _COCUBES_PLAN}
    score = total = 0
    for qid, chosen in answers.items():
        try:
            qid = int(qid)
        except (ValueError, TypeError):
            continue
        q = by_id.get(qid)
        if not q:
            continue
        sec = q["section"]
        if sec not in sec_score:
            continue
        sec_score[sec]["total"] += 1
        if q.get("type") == "code":
            # free-text: not auto-graded, just record attempt
            results[qid] = {"type": "code",
                            "attempted": bool(isinstance(chosen, str) and chosen.strip())}
            continue
        total += 1
        attempted, is_correct, correct_display = _grade_choice(q, chosen, salt)
        if is_correct:
            score += 1
            sec_score[sec]["correct"] += 1
        res = {"correct": is_correct, "section": sec}
        if attempted:
            res["answer"] = correct_display
            res["explanation"] = q["explanation"]
        results[qid] = res
    # Saving the attempt and the certificate are isolated from grading: the
    # score above is final, so a failure there is logged and flagged, never
    # turned into a "Could not grade the test" error on the page.
    from skillup_assessment.services import after_grading
    return JsonResponse({"score": score, "total": total,
                         "percentage": (score * 100 // total) if total else 0,   # rounded down, like the 70% rule
                         "sections": sec_score, "results": results,
                         **after_grading(request.user, 'cocubes', score, total)})

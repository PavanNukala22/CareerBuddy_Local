from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from django.contrib.auth.decorators import login_required
from activities.views import _can_access_workshop, _locked_redirect
from .models import GDSession, GDMessage
from .agents import AGENTS


@login_required
def home(request):
    """Landing page — enter a GD topic and start a session."""

    if not _can_access_workshop(request.user, 'gd'):
        return _locked_redirect()

    if request.user.is_authenticated:
        recent_sessions = GDSession.objects.filter(user=request.user).order_by('-created_at')[:5]
    else:
        recent_sessions = GDSession.objects.none()
    suggested_topics = [
        "Social media is damaging society",
        "AI will replace human jobs",
        "Climate change needs immediate action",
        "Work from home vs office",
        "Is online education effective?"
    ]
    return render(request, 'GD_app/home.html', {
        'recent_sessions': recent_sessions,
        'agents': AGENTS,
        'suggested_topics': suggested_topics
    })


@require_POST
@login_required
def create_session(request):
    if not _can_access_workshop(request.user, 'gd'):
        return _locked_redirect()
        
    """Create a new GD session and redirect to the discussion room."""
    topic = request.POST.get('topic', '').strip()
    if not topic:
        return redirect('GD_app:home')
    
    # Handle anonymous users safely
    user = request.user if request.user.is_authenticated else None
    session = GDSession.objects.create(topic=topic, user=user)
    return redirect('GD_app:gd_room', session_id=session.id)


@login_required
def gd_room(request, session_id):
    """The main Group Discussion room."""
    # Scoped to the requesting user: GDSession.id is a plain sequential
    # AutoField, so without this a session's live room — topic, transcript,
    # everything — is reachable by anyone who can guess or iterate a nearby id.
    session = get_object_or_404(GDSession, id=session_id, user=request.user)
    chat_messages = session.messages.all()
    return render(request, 'GD_app/room.html', {
        'session': session,
        'chat_messages': chat_messages,
        'agents': AGENTS,
    })


@login_required
def session_report(request, session_id):
    """Show post-GD performance report."""
    import math
    # Same ownership scoping as gd_room — the performance report contains
    # personal feedback and a score that belong to exactly one candidate.
    session = get_object_or_404(GDSession, id=session_id, user=request.user)
    report = session.performance_report
    dashoffset = 0
    if report and report.get('overall_score') is not None:
        r = 68
        circumference = 2 * math.pi * r  # ≈ 427.26
        dashoffset = round(circumference - (report['overall_score'] / 100) * circumference, 2)
    return render(request, 'GD_app/report.html', {
        'session': session,
        'report': report,
        'dashoffset': dashoffset,
    })


@login_required
def api_sessions(request):
    """REST endpoint: list the requesting user's own past sessions (for the history page)."""
    # Scoped to the requesting user — this previously listed every session on
    # the platform with no filtering at all, directly disclosing every other
    # user's session ids (and topics) with no guessing required.
    sessions = list(
        GDSession.objects.filter(user=request.user).values('id', 'topic', 'created_at', 'is_active')
    )
    return JsonResponse({'sessions': sessions})
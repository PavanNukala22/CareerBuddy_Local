import json
import logging
import random
import urllib.request
import os
from django.db import models
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Topic, JAMSession, UserProfile, AssessmentGroup
from .forms import SignUpForm, ProfileForm
from django.conf import settings
from core.agents.utils import language_directive
from activities.views import _can_access_workshop, _locked_redirect

logger = logging.getLogger(__name__)

# Import shared transcription utility from the core app
try:
    from core.agents.utils import transcribe_with_sarvam
except ImportError:
    def transcribe_with_sarvam(audio_file, api_key):
        return "", {}, {"message": "core.agents.utils not available", "status": 500}

# Import shared score recording
try:
    from core.models import ScoreRecord
    _HAS_SCORE_RECORD = True
except ImportError:
    _HAS_SCORE_RECORD = False


# Load environment variables from .env file



def get_app_user(request):
    """Helper to get a user for single-user mode."""
    if request.user.is_authenticated:
        return request.user
    return User.objects.first()


JAM_ASSESSMENT_LEVELS = ('easy', 'medium', 'hard')
JAM_ASSESSMENT_LEVEL_LABELS = {
    'easy': 'Simple',
    'medium': 'Intermediate',
    'hard': 'Hard'
}


def get_jam_level_progress(user):
    """Has `user` completed at least one topic at each JAM difficulty?

    The assessment (start_assessment below) is a separate 3-stage flow with
    its own sessions — this checks ordinary practice sessions
    (JAMSession.completed=True, keyed by the topic's difficulty), which is
    what "complete one topic from each level" means before that flow may be
    started. Returns {'easy': bool, 'medium': bool, 'hard': bool}.
    """
    completed_difficulties = set(
        JAMSession.objects.filter(
            user=user,
            completed=True,
            topic__difficulty__in=JAM_ASSESSMENT_LEVELS
        ).values_list(
            'topic__difficulty',
            flat=True
        ).distinct()
    )
    return {
        level: level in completed_difficulties
        for level in JAM_ASSESSMENT_LEVELS
    }


@login_required
def home(request):
    if not _can_access_workshop(request.user, 'jam'):
        return _locked_redirect()

    return redirect('jam:dashboard')


@login_required
@require_POST
def reset_progress(request):
    """Resets the user's progress by deleting all sessions and resetting profile stats."""
    # Was reachable with no CSRF protection AND no login_required, so a
    # forged cross-site request could wipe out an arbitrary logged-in
    # victim's entire JAM history — or, unauthenticated, whichever account
    # get_app_user()'s single-user-mode fallback resolves to.
    user = get_app_user(request)
    profile = get_object_or_404(UserProfile, user=user)
    
    # Delete all sessions for this user
    JAMSession.objects.filter(user=user).delete()
    
    # Reset profile stats
    profile.total_sessions = 0
    profile.total_minutes = 0
    profile.save()
    
    messages.success(request, "All progress has been reset successfully.")
    return redirect('jam:dashboard')


def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f'Welcome to JAM English, {user.username}!')
            return redirect('jam:dashboard')
    else:
        form = SignUpForm()
    return render(request, 'jam/signup.html', {'form': form})


@login_required
def dashboard(request):
    if not _can_access_workshop(request.user, 'jam'):
        return _locked_redirect()
    profile, _ = UserProfile.objects.get_or_create(user=get_app_user(request))
    recent_sessions = JAMSession.objects.filter(user=get_app_user(request), completed=True)[:5]
    total_sessions = JAMSession.objects.filter(user=get_app_user(request), completed=True).count()
    total_topics = Topic.objects.filter(is_active=True).count()

    recent_session = recent_sessions.first()
    recent_score = recent_session.overall_score_display if recent_session else None

    sessions_with_scores = JAMSession.objects.filter(
        user=get_app_user(request), completed=True,
        confidence_score__isnull=False
    )
    
    avg_overall = 0
    if sessions_with_scores.exists():
        total_overall = sum(s.overall_score_display for s in sessions_with_scores if s.overall_score_display)
        avg_overall = round(total_overall / sessions_with_scores.count(), 1)

    level_progress = get_jam_level_progress(get_app_user(request))

    has_easy = level_progress['easy']
    has_medium = level_progress['medium']
    has_hard = level_progress['hard']
    can_start_assessment = all(level_progress.values())

    context = {
        'profile': profile,
        'recent_sessions': recent_sessions,
        'total_sessions': total_sessions,
        'total_topics': total_topics,
        'recent_score': recent_score,
        'avg_overall': avg_overall,
        # Passed as individual booleans so the template can check each one.
        'easy_done': level_progress['easy'],
        'medium_done': level_progress['medium'],
        'hard_done': level_progress['hard'],
        'assessment_unlocked': all(level_progress.values()),

        # Compatibility with the existing dashboard template.
        'has_easy': has_easy,
        'has_medium': has_medium,
        'has_hard': has_hard,
        'can_start_assessment': can_start_assessment,
    }
    return render(request, 'jam/dashboard.html', context)


def jam_session(request):
    topics = Topic.objects.filter(is_active=True)
    if not topics.exists():
        messages.warning(request, 'No topics available. Please ask admin to add topics.')
        return redirect('jam:dashboard')

    topic = random.choice(list(topics))
    session = JAMSession.objects.create(user=get_app_user(request), topic=topic)
    return render(request, 'jam/session.html', {'topic': topic, 'session': session})


def jam_session_with_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id, is_active=True)
    session = JAMSession.objects.create(user=get_app_user(request), topic=topic)
    return render(request, 'jam/session.html', {'topic': topic, 'session': session})


@require_POST
def save_audio(request):
    session_id = request.POST.get('session_id')
    audio_file = request.FILES.get('audio')
    duration = request.POST.get('duration', 0)

    try:
        session = JAMSession.objects.get(id=session_id, user=get_app_user(request))
        if audio_file:
            session.audio_file = audio_file
        session.duration = int(duration)
        # session.html has always posted this from the header dropdown; it was
        # discarded here, so feedback came back in English whatever the learner
        # selected. Persisted because feedback is generated in a later request.
        session.language = (request.POST.get('language') or 'english').strip().lower()
        transcript = request.POST.get('transcript', '').strip()
        
        # Backend Transcription Fallback if frontend failed
        if not transcript and audio_file and getattr(settings, "SARVAM_API_KEY", None):
            # We need to seek(0) because the file might have been read during the FileField assignment
            audio_file.seek(0)
            stt_text, _, _ = transcribe_with_sarvam(audio_file, settings.SARVAM_API_KEY)
            if stt_text:
                transcript = stt_text

        if transcript:
            session.transcript = transcript
        session.save()
        return JsonResponse({'status': 'ok', 'session_id': session.id})
    except JAMSession.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)


def start_assessment(request):
    """Initializes a 3-stage Assessment journey.

    Gated on the user having completed one practice topic at each
    difficulty first (see get_jam_level_progress) — the assessment is meant
    to diagnose consistency across levels the learner has already practiced,
    not to be someone's first attempt at a Hard topic.
    """
    user = get_app_user(request)
    level_progress = get_jam_level_progress(user)
    if not all(level_progress.values()):
        missing = [
            JAM_ASSESSMENT_LEVEL_LABELS[level]
            for level in JAM_ASSESSMENT_LEVELS if not level_progress[level]
        ]
        messages.error(
            request,
            "Complete one topic from each of the three levels (Simple, Intermediate, Hard) "
            "before starting the assessment. Still pending: " + ", ".join(missing) + "."
        )
        return redirect('jam:dashboard')

    easy_topics   = list(Topic.objects.filter(difficulty='easy',   is_active=True))
    medium_topics = list(Topic.objects.filter(difficulty='medium', is_active=True))
    hard_topics   = list(Topic.objects.filter(difficulty='hard',   is_active=True))

    if not (easy_topics and medium_topics and hard_topics):
        messages.error(request, "Need topics of all difficulties (Easy, Medium, Hard) to start assessment.")
        return redirect('jam:dashboard')
        
    has_easy = JAMSession.objects.filter(user=get_app_user(request), completed=True, topic__difficulty='easy').exists()
    has_medium = JAMSession.objects.filter(user=get_app_user(request), completed=True, topic__difficulty='medium').exists()
    has_hard = JAMSession.objects.filter(user=get_app_user(request), completed=True, topic__difficulty='hard').exists()
    
    if not (has_easy and has_medium and has_hard):
        messages.error(request, "You must complete at least one Simple, one Intermediate, and one Hard practice topic before starting an assessment.")
        return redirect('jam:dashboard')

    easy_sess = JAMSession.objects.create(user=get_app_user(request), topic=random.choice(easy_topics))
    med_sess  = JAMSession.objects.create(user=get_app_user(request), topic=random.choice(medium_topics))
    hard_sess = JAMSession.objects.create(user=get_app_user(request), topic=random.choice(hard_topics))

    group = AssessmentGroup.objects.create(
        user=get_app_user(request),
        easy_session=easy_sess,
        medium_session=med_sess,
        hard_session=hard_sess
    )

    messages.info(request, "🚀 Assessment started! Stage 1: Easy Topic.")
    return redirect('jam:assessment_session', session_id=easy_sess.id)


def assessment_session(request, session_id):
    """View specifically for assessment steps."""
    session = get_object_or_404(JAMSession, id=session_id, user=get_app_user(request))
    group = AssessmentGroup.objects.filter(
        Q(easy_session=session) | Q(medium_session=session) | Q(hard_session=session)  # type: ignore
    ).first()

    if not group:
        return redirect('jam:jam_session_with_topic', topic_id=session.topic.id)

    stage = 1
    if group.medium_session == session: stage = 2
    elif group.hard_session == session: stage = 3

    return render(request, 'jam/session.html', {
        'topic': session.topic,
        'session': session,
        'is_assessment': True,
        'stage': stage,
        'assessment_id': group.id
    })



# ── Sarvam AI Feedback ────────────────────────────────────────────────────────


def generate_ai_feedback_sarvam(session, total_sessions):
    """
    Calls Sarvam AI API to evaluate a JAM speech across 5 categories.
    Returns structured JSON feedback or falls back to rule-based feedback.
    """
    difficulty  = session.topic.difficulty if session.topic else 'medium'
    topic_name  = str(session.topic)      if session.topic else 'your topic'

    api_key = getattr(settings, "SARVAM_API_KEY", None)
    api_url = getattr(settings, "SARVAM_API_URL", "https://api.sarvam.ai/v1/chat/completions")
    model_name = getattr(settings, "SARVAM_MODEL", "sarvam-105b")

    if not api_key:
        # Fallback to rule-based feedback
        return _rule_based_feedback(session, total_sessions, topic_name, difficulty)

    transcript  = session.transcript or ""
    if not transcript.strip():
        # Set scores to 0 if there is no speech
        session.confidence_score = 0
        session.fluency_score = 0
        session.language_score = 0
        session.pronunciation_score = 0
        session.time_management_score = 0
        session.save()
        return f"<h4 class='feedback-highlight'><b>Performance Analysis — '{topic_name}'</b></h4>\n📝 <b>Feedback</b>: No speech detected. Please try to speak clearly into your microphone during the next session."

    duration    = session.duration

    prompt = f"""You are an elite communication coach and linguist evaluating a JAM (Just A Minute) speech.
Your goal is to provide a FAIR, objective, and detailed assessment.

Topic: "{topic_name}" (Expected difficulty level: {difficulty})
Duration spoken: {duration} seconds
Session number: {total_sessions}

Transcript to evaluate:
"{transcript}"

Evaluation Criteria (Score 0-5, give 0 for no speech or completely irrelevant):
1. Confidence: Does the speaker sound sure and steady? (0-5)
2. Fluency: Are there excessive pauses, 'um's, or 'ah's? (0-5)
3. Language: Is the vocabulary appropriate? Are there grammar errors? (0-5)
4. Pronunciation: Is the speech clear and understandable? (0-5)
5. Time Management: How close did they get to 60 seconds? (0-5)

Return ONLY valid JSON:
{{
  "confidence": {{"score": <0-5>, "analysis": "<detailed analysis>", "improvement": "<specific tip>"}},
  "fluency":    {{"score": <0-5>, "analysis": "<detailed analysis>", "improvement": "<specific tip>"}},
  "language":   {{"score": <0-5>, "analysis": "<detailed analysis>", "improvement": "<specific tip>"}},
  "pronunciation": {{"score": <0-5>, "analysis": "<detailed analysis>", "improvement": "<specific tip>"}},
  "time_management": {{"score": <0-5>, "analysis": "<detailed analysis>", "improvement": "<specific tip>"}},
  "overall_score": <sum of all 5 scores>,
  "is_unrelated": <true if the speech is completely off-topic, else false>,
  "overall_feedback": "<encouraging summary>",
  "vocabulary_grammar": "<specific linguistic feedback>",
  "improvement_roadmap": ["<step 1>", "<step 2>", "<step 3>"]
}}{language_directive(getattr(session, 'language', 'english'))}"""

    try:
        payload = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 800,
            "temperature": 0.4,
            "reasoning_effort": None,
        }).encode("utf-8")

        req = urllib.request.Request(
            api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "api-subscription-key": api_key,
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        raw_text = data["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        result = json.loads(raw_text)
        
        # Save scores to session object
        session.confidence_score = result.get("confidence", {}).get("score", 0)
        session.fluency_score = result.get("fluency", {}).get("score", 0)
        session.language_score = result.get("language", {}).get("score", 0)
        session.pronunciation_score = result.get("pronunciation", {}).get("score", 0)
        session.time_management_score = result.get("time_management", {}).get("score", 0)
        
        # Save improvement roadmap separately
        roadmap = result.get("improvement_roadmap", [])
        session.improvement_tips = "\n".join([f"- {step}" for step in roadmap])
        
        session.save() # Crucial: persists the scores to DB
        
        return _format_ai_feedback(result, topic_name, total_sessions, difficulty)

    except Exception as e:
        # Fallback to rule-based feedback
        return _rule_based_feedback(session, total_sessions, topic_name, difficulty)


def _format_ai_feedback(result, topic_name, total_sessions, difficulty):
    """Formats parsed Sarvam JSON into a readable feedback string."""
    def stars(n):
        n = int(round(n))
        return "★" * n + "☆" * (5 - n)

    c  = result.get("confidence",       {})
    f  = result.get("fluency",          {})
    l  = result.get("language",         {})
    p  = result.get("pronunciation",    {})
    t  = result.get("time_management",  {})
    overall = result.get("overall_score", 0)
    is_unrelated = result.get("is_unrelated", False)
    if is_unrelated:
        return f"<h4 class='feedback-highlight'><b>Performance Analysis — '{topic_name}'</b></h4>\n📝 <b>Feedback</b>: I’m not sure I understand. This seems unrelated to the topic of '{topic_name}'. Please try to stay on topic for a better score!"

    summary = result.get("overall_feedback", "")
    vocab_grammar = result.get("vocabulary_grammar", "Your vocabulary was appropriate for the topic level.")

    roadmap = result.get("improvement_roadmap", [])
    lines = [
        f"<h4 class='feedback-highlight'><b>Performance Analysis — '{topic_name}'</b></h4>",
        f"📝 <b>Feedback</b>: {summary}",
        f"📚 <b>Vocabulary & Grammar</b>: {vocab_grammar}"
    ]
    return "\n".join(lines)



def _rule_based_feedback(session, total_sessions, topic_name, difficulty):
    """Fallback rule-based feedback when API is unavailable."""
    duration   = session.duration
    transcript = session.transcript or ""
    word_count = len(transcript.split()) if transcript else 0

    if word_count == 0:
        # No speech was captured, so there is nothing to grade. Previously this
        # only applied under 5 seconds; a longer silent/failed session fell
        # through and scored duration-based marks — always 2+2+1+3+5 = 13/25,
        # including 5/5 for "time management" and 3/5 for pronunciation on an
        # empty recording. Score every criterion 1 instead: sitting on the page
        # is not a performance.
        session.confidence_score = 0
        session.fluency_score = 0
        session.language_score = 0
        session.pronunciation_score = 0
        session.time_management_score = 0
        session.save()
        return f"<h4 class='feedback-highlight'><b>Performance Analysis — '{topic_name}'</b></h4>\n📝 <b>Feedback</b>: No speech detected. Please check that your microphone is working and allowed for this site, then speak clearly during the next session."

    # Calculate scores based on performance (Rule-based Fallback)
    time_mgmt = 5 if duration >= 50 else 4 if duration >= 40 else 3 if duration >= 25 else 2 if duration >= 10 else 1

    # Estimate fluency based on words per minute (target ~100-130 WPM)
    wpm = (word_count / duration * 60) if duration > 0 else 0

    fluency = 5 if wpm >= 110 else 4 if wpm >= 80 else 3 if wpm >= 50 else 2 if wpm >= 20 else 1
    language = 4 if word_count > 80 else 3 if word_count > 40 else 2 if word_count > 15 else 1
    confidence = 4 if duration > 45 and wpm > 70 else 3 if duration > 30 else 2

    # No rule-based signal for pronunciation, so scale it with how much was
    # actually said rather than handing out a flat 3/5 to every session.
    pronun = 4 if word_count > 80 else 3 if word_count > 30 else 2
    
    # Save scores to session object
    session.confidence_score = confidence
    session.fluency_score = fluency
    session.language_score = language
    session.pronunciation_score = pronun
    session.time_management_score = time_mgmt
    
    overall = confidence + fluency + language + pronun + time_mgmt

    fluency_line = (
        "Your speech was exceptionally smooth and well-paced." if fluency >= 4
        else "Good flow overall, though some pauses were noticeable." if fluency >= 3
        else "Focus on reducing hesitations and building rhythm."
    )
    lang_line = (
        "Excellent vocabulary and grammar throughout." if language >= 4
        else "Good language use with minor errors." if language >= 3
        else "Work on expanding vocabulary and sentence variety."
    )
    pronun_line = (
        "Very clear and native-like pronunciation." if pronun >= 4
        else "Pronunciation was acceptable with some areas to refine." if pronun >= 3
        else "Focus on phoneme accuracy and word stress patterns."
    )
    time_line = (
        "Excellent use of the full minute — well done!" if time_mgmt >= 4 and duration >= 50
        else "Good pacing, but try to use the full 60 seconds." if time_mgmt >= 3
        else "Use transitional phrases like 'Furthermore...' to fill the minute."
    )

    # Dynamic Improvement Roadmap for Fallback
    roadmap = []
    if duration < 50:
        roadmap.append(f"<span class='feedback-highlight'><b>1. Pacing</b></span>: You spoke for {duration}s. Try to extend your thoughts to reach the full 60 seconds.")
    else:
        roadmap.append("<span class='feedback-highlight'><b>1. Pacing</b></span>: Great job hitting the time target! Now focus on adding a strong concluding sentence.")
        
    if wpm < 80:
        roadmap.append(f"<span class='feedback-highlight'><b>2. Fluency</b></span>: Your speed was a bit slow ({int(wpm)} WPM). Try to reduce mid-sentence pauses.")
    elif wpm > 150:
        roadmap.append("<span class='feedback-highlight'><b>2. Fluency</b></span>: You spoke very fast. Try to slow down slightly to improve clarity.")
    else:
        roadmap.append("<span class='feedback-highlight'><b>2. Fluency</b></span>: Good rhythm! To improve further, try varying your pitch for emphasis.")

    if word_count < 60:
        roadmap.append(f"<span class='feedback-highlight'><b>3. Content</b></span>: You used {word_count} words. Try to add 2-3 specific examples to make your JAM more engaging.")
    else:
        roadmap.append("<span class='feedback-highlight'><b>3. Content</b></span>: Good depth! Try using more advanced connectives like 'conversely' or 'consequently'.")

    # Save roadmap to session object
    session.improvement_tips = "\n".join(roadmap)
    session.save() # Persist fallback scores

    # Dynamic feedback templates to ensure variety
    feedback_options = {
        "high": [
            f"Excellent performance! You handled the topic of '{topic_name}' with great confidence and flow.",
            f"Brilliant delivery! Your thoughts on '{topic_name}' were well-structured and very engaging.",
            f"Masterful JAM session! You dominated the topic of '{topic_name}' with professional clarity."
        ],
        "med": [
            f"Good effort on '{topic_name}'! Focus on expanding your ideas further and maintaining a steady pace.",
            f"Steady progress! You have a good grasp of '{topic_name}', now work on reducing minor hesitations.",
            f"Solid attempt at '{topic_name}'. Try to add more descriptive details to make your speech shine."
        ],
        "low": [
            f"Nice attempt at '{topic_name}'. Work on building fluency and using the full 60 seconds next time.",
            f"Building blocks! Keep practicing topics like '{topic_name}' to improve your confidence and stamina.",
            f"Good start. For '{topic_name}', try to prepare 2-3 key points before you start speaking to fill the time."
        ]
    }

    if overall >= 20:
        overall_desc = random.choice(feedback_options["high"])
    elif overall >= 13:
        overall_desc = random.choice(feedback_options["med"])
    else:
        overall_desc = random.choice(feedback_options["low"])

    return "\n".join([
        f"<h4 class='feedback-highlight'><b>Performance Analysis — '{topic_name}'</b></h4>",
        f"📝 <b>Feedback</b>: {overall_desc}"
    ])


def generate_final_assessment(group):
    """Synthesizes data from 3 sessions into a final report."""
    sessions = [group.easy_session, group.medium_session, group.hard_session]
    avg_duration = sum(s.duration for s in sessions) / 3
    avg_fluency  = sum(s.fluency_score or 3 for s in sessions) / 3

    if avg_fluency >= 4.5:
        level = "Advanced"
    elif avg_fluency >= 3.5:
        level = "Intermediate"
    else:
        level = "Beginner"

    diagnostic_text = (
        f"You handle <b>{group.easy_session.topic}</b> with ease. "
        f"However, when difficulty increased to <b>{group.hard_session.topic}</b>, "
        "we noticed a slight dip in structure — this is a great focus area."
        if avg_duration < 50
        else "You maintained strong, consistent pacing across all three difficulty levels — a sign of a skilled communicator."
    )

    score_display = round(avg_fluency, 1)

    # Collect per-session specific improvements if AI returned them
    per_session_tips = []
    labels = ["Easy", "Medium", "Hard"]
    for label, sess in zip(labels, sessions):
        if sess and sess.ai_feedback:
            # Extract overall_feedback snippet from stored html (brief summary only)
            per_session_tips.append(
                f"<li><b>{label} Stage ({sess.topic})</b>: Overall score {sess.overall_score_display}/25</li>"
            )

    summary_items = "\n".join(per_session_tips) if per_session_tips else (
        f"<li><b>Easy ({group.easy_session.topic})</b>: {group.easy_session.overall_score_display}/25</li>"
        f"<li><b>Medium ({group.medium_session.topic})</b>: {group.medium_session.overall_score_display}/25</li>"
        f"<li><b>Hard ({group.hard_session.topic})</b>: {group.hard_session.overall_score_display}/25</li>"
    )

    report = [
        f"<h4 class='feedback-highlight'><b>🏆 Result Level: {level}</b></h4>",
        "<p>Congratulations on completing the 3-stage JAM assessment!</p>",
        "<h3>📈 Overall Statistics</h3>",
        "<ul>",
        f"<li><b>Average Duration</b>: {int(avg_duration)}s per topic</li>",
        f"<li><b>Average Fluency Consistency</b>: {score_display}/5 → <b>{level}</b></li>",
        summary_items,
        "</ul>",
        "<h3>🔍 Diagnostic Profile</h3>",
        f"<p>{diagnostic_text}</p>",
        "<h3>🚀 Next Steps for You</h3>",
        "<ul>",
        "<li><b>Vocabulary</b>: Practice synonyms for common words to avoid repetition in Hard topics.</li>",
        "<li><b>Pacing</b>: Use the full 60 seconds even on Easy topics to build stamina.</li>",
        "<li><b>Tone</b>: Work on varying your pitch to sound more engaging.</li>",
        "</ul>",
    ]
    return "\n".join(report)




def complete_session(request, session_id):
    """Marks session as complete, generates AI feedback, and redirects to results."""
    session = get_object_or_404(JAMSession, id=session_id, user=get_app_user(request))
    profile, _ = UserProfile.objects.get_or_create(user=get_app_user(request))
    
    if not session.completed:
        logger.debug("Marking JAM session %s as completed.", session.id)
        session.completed = True
        profile.total_sessions += 1
        profile.total_minutes += session.duration // 60
        profile.save()

    # Generate Sarvam AI feedback (ensure it happens even if already completed)
    logger.debug(
        "Analyzing JAM session %s. Duration: %ss. Transcript length: %s",
        session.id, session.duration, len(session.transcript or ''),
    )

    if not session.ai_feedback or session.confidence_score is None:
        logger.debug("Triggering AI feedback generation for JAM session %s", session.id)
        session.ai_feedback = generate_ai_feedback_sarvam(session, profile.total_sessions)

        # Final sanity check: if scores are still missing, force rule-based
        if session.confidence_score is None or session.confidence_score == 0:
            logger.debug("Scores missing after AI call, forcing rule-based fallback for JAM session %s", session.id)
            topic_name = session.topic.title if session.topic else "topic"
            diff = session.topic.difficulty if session.topic else "medium"
            _rule_based_feedback(session, 0, topic_name, diff)

        session.save()
        logger.debug("JAM session %s analysis complete. Confidence: %s", session.id, session.confidence_score)

        # Create ScoreRecord for the main dashboard
        try:
            if _HAS_SCORE_RECORD:
                score_val = session.overall_score_display or 0
                ScoreRecord.objects.create(
                    user=get_app_user(request),
                    module='jam',
                    score=score_val,
                    max_score=25,
                    label=f"JAM: {session.topic.title}"[:200]
                )
        except Exception:
            logger.exception("Error saving JAM ScoreRecord for session %s", session.id)

    else:
        logger.debug("JAM session %s already has analysis. Skipping re-generation.", session.id)


    # Check for assessment flow
    group = AssessmentGroup.objects.filter(
        Q(easy_session=session) | Q(medium_session=session) | Q(hard_session=session)  # type: ignore
    ).first()

    if group:
        if group.easy_session == session:
            messages.success(request, '✅ Stage 1 Complete! Now for Stage 2: Medium.')
            return redirect('jam:assessment_session', session_id=group.medium_session.id)
        elif group.medium_session == session:
            messages.success(request, '✅ Stage 2 Complete! Almost there... Stage 3: Hard.')
            return redirect('jam:assessment_session', session_id=group.hard_session.id)
        else:
            group.completed = True
            group.final_report = generate_final_assessment(group)
            group.save()
            messages.success(request, '🎉 Assessment Complete! View your final report below.')
            return redirect('jam:assessment_result', assessment_id=group.id)

    messages.success(request, '🎉 Session saved! Your feedback is ready below.')
    return redirect(reverse('jam:session_detail', args=[session.id]) + '#ai-feedback')


def assessment_result(request, assessment_id):
    """Shows the final diagnostic report."""
    group = get_object_or_404(AssessmentGroup, id=assessment_id, user=get_app_user(request))
    stages = [
        ("Easy Stage — " + (group.easy_session.topic.title if group.easy_session and group.easy_session.topic else "Easy"), group.easy_session),
        ("Medium Stage — " + (group.medium_session.topic.title if group.medium_session and group.medium_session.topic else "Medium"), group.medium_session),
        ("Hard Stage — " + (group.hard_session.topic.title if group.hard_session and group.hard_session.topic else "Hard"), group.hard_session),
    ]
    return render(request, 'jam/assessment_result.html', {'assessment': group, 'stages': stages})


@login_required
def session_detail(request, session_id):
    session = get_object_or_404(JAMSession, id=session_id, user=get_app_user(request))
    assessment = AssessmentGroup.objects.filter(
        Q(easy_session=session) | Q(medium_session=session) | Q(hard_session=session)  # type: ignore
    ).first()
    return render(request, 'jam/session_detail.html', {
        'session': session,
        'assessment': assessment
    })


@login_required
def history(request):
    regular_sessions = JAMSession.objects.filter(
        user=get_app_user(request),
        completed=True,
        assessment_easy__isnull=True,
        assessment_medium__isnull=True,
        assessment_hard__isnull=True
    )
    assessments = AssessmentGroup.objects.filter(user=get_app_user(request), completed=True)
    return render(request, 'jam/history.html', {
        'sessions': regular_sessions,
        'assessments': assessments
    })


def topics_list(request):
    topics = Topic.objects.filter(is_active=True).order_by('difficulty', 'title')
    easy   = topics.filter(difficulty='easy')
    medium = topics.filter(difficulty='medium')
    hard   = topics.filter(difficulty='hard')
    return render(request, 'jam/topics.html', {'easy': easy, 'medium': medium, 'hard': hard})


def profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=get_app_user(request))
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save()
            user = get_app_user(request)
            user.first_name = form.cleaned_data.get('first_name', '')
            user.last_name  = form.cleaned_data.get('last_name', '')
            user.email      = form.cleaned_data.get('email', '')
            user.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('jam:profile')
    else:
        form = ProfileForm(instance=profile)

    sessions = JAMSession.objects.filter(user=get_app_user(request), completed=True)
    return render(request, 'jam/profile.html', {'form': form, 'profile': profile, 'sessions': sessions})


def logout_view(request):
    logout(request)
    return redirect('login')


@require_POST
def delete_session(request, session_id):
    session = get_object_or_404(JAMSession, id=session_id, user=get_app_user(request))
    profile, _ = UserProfile.objects.get_or_create(user=get_app_user(request))
    if session.completed:
        if profile.total_sessions > 0:
            profile.total_sessions -= 1
        minutes_to_subtract = session.duration // 60
        if profile.total_minutes >= minutes_to_subtract:
            profile.total_minutes -= minutes_to_subtract
        else:
            profile.total_minutes = 0
        profile.save()
    if session.audio_file:
        session.audio_file.delete()
    session.delete()
    messages.success(request, "Your practice session has been removed from history.")
    return redirect(request.META.get('HTTP_REFERER', 'jam:dashboard'))




@require_POST
def delete_assessment(request, assessment_id):
    assessment = get_object_or_404(AssessmentGroup, id=assessment_id, user=get_app_user(request))
    profile, _ = UserProfile.objects.get_or_create(user=get_app_user(request))
    sessions = [assessment.easy_session, assessment.medium_session, assessment.hard_session]
    for session in sessions:
        if session and session.completed:
            if profile.total_sessions > 0:
                profile.total_sessions -= 1
            minutes_to_subtract = session.duration // 60
            if profile.total_minutes >= minutes_to_subtract:
                profile.total_minutes -= minutes_to_subtract
            else:
                profile.total_minutes = 0
            if session.audio_file:
                session.audio_file.delete()
            session.delete()
    profile.save()
    assessment.delete()
    messages.success(request, "Assessment and its practice sessions have been removed.")
    return redirect('jam:history')
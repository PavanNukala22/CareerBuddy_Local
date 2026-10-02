from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.core.cache import cache
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import RegisterForm, LoginForm, ProfileUpdateForm
from activities.models import UserProgress, UserExerciseResult, Activity
from core.email_utils import send_transactional_email, is_valid_email
from core.otp_utils import generate_and_send_otp, verify_otp
from decouple import config

# Session key holding the list of email addresses the visitor has proven control
# of by OTP. A list (not a single value) so a form with more than one email — the
# employer signup has both an account email and an HR email — can verify each.
OTP_VERIFIED_SESSION_KEY = 'otp_verified_emails'


def _normalize_email(value):
    return (value or '').strip().lower()


def _mark_email_verified(request, email):
    """Record that `email` was verified by OTP in this session."""
    verified = request.session.get(OTP_VERIFIED_SESSION_KEY) or []
    norm = _normalize_email(email)
    if norm and norm not in verified:
        verified.append(norm)
        request.session[OTP_VERIFIED_SESSION_KEY] = verified


def is_email_verified(request, email):
    """True when `email` was verified by OTP in this session."""
    return _normalize_email(email) in (request.session.get(OTP_VERIFIED_SESSION_KEY) or [])


def clear_verified_emails(request):
    request.session.pop(OTP_VERIFIED_SESSION_KEY, None)


# Per-IP cap on OTP sends. The per-address 60s cooldown alone does not stop one
# client cycling through many victim addresses (email bombing) — that both spams
# real people and burns the transactional-email quota. This bounds how many
# addresses a single source can trigger a send to per window.
# Overridable via environment for automated QA/CI runs, which legitimately send
# far more OTPs per IP than any real user would in the same window; production
# keeps the same defaults (8 / 600s) unless the environment explicitly overrides them.
MAX_OTP_SENDS_PER_IP = config('MAX_OTP_SENDS_PER_IP', default=8, cast=int)
OTP_SEND_WINDOW_SECONDS = config('OTP_SEND_WINDOW_SECONDS', default=600, cast=int)


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def _bump_ip_send_count(ip_key):
    try:
        cache.incr(ip_key)
    except ValueError:
        cache.set(ip_key, 1, OTP_SEND_WINDOW_SECONDS)


@require_POST
def send_email_otp(request):
    """AJAX: email a fresh OTP to the address the visitor entered on the form.

    The HTTP response is deliberately the SAME whether or not the address is
    already registered, so this endpoint is not an account-existence oracle: an
    attacker cannot tell a taken email from a free one by its reply. A genuinely
    registered address instead receives an "account exists" notice by email
    (the same pattern password-reset flows use), and the final registration
    submit still enforces one-account-per-email.
    """
    email = (request.POST.get('email') or '').strip()

    # Throttle by source IP first, on every path, to blunt email-bombing.
    ip_key = f'otp_send_ip:{_client_ip(request)}'
    if cache.get(ip_key, 0) >= MAX_OTP_SENDS_PER_IP:
        return JsonResponse(
            {'ok': False, 'error': 'Too many verification requests. Please try again later.'},
            status=429,
        )

    # A malformed address is a format error, not an enumeration signal, so it is
    # safe (and clearer) to report it directly.
    if not is_valid_email(email):
        return JsonResponse({'ok': False, 'error': 'Please enter a valid email address.'}, status=400)

    # Identical reply for both branches — never leak whether the email is taken.
    neutral = {'ok': True, 'message': 'A verification code has been sent if this email can be registered. Please check your inbox.'}

    if User.objects.filter(email__iexact=email).exists():
        try:
            send_transactional_email(
                subject='You already have a Career Buddy account',
                to_email=email,
                template_name='emails/account_exists.html',
                context={'login_url': request.build_absolute_uri(reverse('login'))},
            )
        except Exception:
            pass
        _bump_ip_send_count(ip_key)
        return JsonResponse(neutral)

    ok, _message = generate_and_send_otp(email)
    if ok:
        _bump_ip_send_count(ip_key)
        return JsonResponse(neutral)
    # A cooldown/transient send failure is reported the same way for any address.
    return JsonResponse(
        {'ok': False, 'error': 'Please wait a moment before requesting another code.'},
        status=429,
    )


@require_POST
def verify_email_otp(request):
    """AJAX: check the OTP and, on success, record the verified email in the session.

    The verified address is what register_view trusts — a hidden form field could
    be forged, so entitlement to register lives server-side, not in the POST body.
    """
    email = (request.POST.get('email') or '').strip()
    code = (request.POST.get('otp') or '').strip()
    ok, message = verify_otp(email, code)
    if ok:
        _mark_email_verified(request, email)
    return JsonResponse({'ok': ok, 'message' if ok else 'error': message}, status=200 if ok else 400)


def send_welcome_email(request, user):
    """Sends a styled welcome email to the newly registered candidate."""
    dashboard_url = request.build_absolute_uri(reverse('student_dashboard'))
    send_transactional_email(
        subject='Welcome to Career Buddy - Registration Successful!',
        to_email=user.email,
        template_name='emails/registration_success.html',
        context={
            'user': user,
            'dashboard_url': dashboard_url,
            'profile': user.profile,
        },
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        # One account per email: if the email already exists, show an error and stay on the page.
        email = request.POST.get('email', '').strip()
        form = RegisterForm(request.POST, request.FILES)
        
        if email and User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'This email ID is already in use. Please use a different email ID.')
            form.add_error('email', 'This email ID is already in use.')
            return render(request, 'users/register.html', {'form': form, 'email_exists_error': True})
        elif not is_email_verified(request, email):
            # The email must be one the visitor verified by OTP. Editing the
            # field after verifying (or skipping it) lands here rather than
            # creating an account against an unconfirmed address.
            messages.error(request, 'Please verify your email address with the OTP before creating your account.')
            form.add_error('email', 'Verify this email address to continue.')
            return render(request, 'users/register.html', {'form': form, 'email_unverified_error': True})
        elif form.is_valid():
            user = form.save()
            # The address is confirmed and consumed — don't let it authorise a second signup.
            clear_verified_emails(request)
            # form.save() doesn't run authenticate(), so user.backend is unset;
            # with multiple AUTHENTICATION_BACKENDS, login() needs one specified.
            user.backend = 'users.backends.EmailOrUsernameModelBackend'
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name}! Your account has been created.')

            # Send welcome email asynchronously or synchronously with graceful handling
            send_welcome_email(request, user)

            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})


# SR-07 fix: brute-force lockout. Keyed by client IP + the submitted username
# so one bad actor guessing many usernames from one IP is throttled by the
# per-IP key, while a distributed attacker hammering one specific account is
# throttled by the per-username key — either key tripping blocks the attempt.
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60


def _login_failure_keys(request, username):
    ip = _client_ip(request)
    uname = (username or '').strip().lower()
    return [f'login_fail:ip:{ip}', f'login_fail:user:{uname}'] if uname else [f'login_fail:ip:{ip}']


def _login_is_locked_out(request, username):
    return any(cache.get(k, 0) >= LOGIN_FAILURE_LIMIT for k in _login_failure_keys(request, username))


def _record_login_failure(request, username):
    for key in _login_failure_keys(request, username):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, LOGIN_LOCKOUT_SECONDS)


def _clear_login_failures(request, username):
    for key in _login_failure_keys(request, username):
        cache.delete(key)


def _safe_next(request):
    """Return the validated ``?next=`` destination, or '' if there isn't one.

    ``next`` is reflected into a redirect, so it is checked with Django's own
    host/scheme validator: without it any landing-page link could be rewritten
    into ``/users/login/?next=https://evil.example`` and the login form would
    bounce the candidate off-site (open redirect). A ``next`` pointing back at
    the login page itself is dropped as well, which is what would otherwise
    produce a login -> login redirect loop.
    """
    candidate = request.POST.get('next') or request.GET.get('next') or ''
    if not candidate:
        return ''
    if not url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return ''
    if candidate.split('?')[0].rstrip('/') == reverse('login').rstrip('/'):
        return ''
    return candidate


def login_view(request):
    next_url = _safe_next(request)
    if request.user.is_authenticated:
        # Honour `next` here too: a candidate who is already signed in and
        # follows a protected landing-page link must land on that destination,
        # not be bounced to the home page.
        return redirect(next_url or 'home')
    if request.method == 'POST':
        submitted_username = request.POST.get('username', '')
        if _login_is_locked_out(request, submitted_username):
            messages.error(request, 'Too many failed login attempts. Please try again in a few minutes.')
            form = LoginForm()
            return render(request, 'users/login.html', {'form': form, 'next': next_url})
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            _clear_login_failures(request, submitted_username)
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(next_url or 'home')
        else:
            _record_login_failure(request, submitted_username)
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {'form': form, 'next': next_url})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    # An employer session must not reach the candidate profile. activities.dashboard
    # already guards itself this way (BR-03); this page had only @login_required, so
    # an employer could open it directly at 200 OK even though no link leads there.
    if request.session.get('portal') == 'employer' or hasattr(request.user, 'employer_profile'):
        return redirect('job_home')

    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            # Save User fields
            request.user.first_name = form.cleaned_data.get('first_name', request.user.first_name)
            request.user.last_name = form.cleaned_data.get('last_name', request.user.last_name)
            request.user.email = form.cleaned_data.get('email', request.user.email)
            request.user.save()
            
            # Save UserProfile fields
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileUpdateForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })

    completed_sub_ids = set(UserProgress.objects.filter(user=request.user, status='completed').values_list('sub_activity_id', flat=True))
    exercise_completed_sub_ids = set(UserExerciseResult.objects.filter(user=request.user).values_list('exercise__sub_activity_id', flat=True))
    completed_sub_ids.update(exercise_completed_sub_ids)
    completed_subs = len(completed_sub_ids)
    all_results = UserExerciseResult.objects.filter(user=request.user)
    total_score = sum(r.score for r in all_results)
    activities_started = Activity.objects.filter(
        subactivities__id__in=completed_sub_ids
    ).distinct().count()

    context = {
        'form': form,
        'profile': profile,
        'completed_subs': completed_subs,
        'total_score': total_score,
        'activities_started': activities_started,
        'recent_results': all_results.order_by('-completed_at')[:10],
    }
    return render(request, 'users/profile.html', context)

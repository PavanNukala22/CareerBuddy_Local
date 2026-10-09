import math
import re
import hmac
import json
import uuid
import hashlib
import logging
import requests
import razorpay
from django.utils import timezone
from functools import reduce
from operator import or_
from django.shortcuts import render, redirect, get_object_or_404
from core.email_utils import send_transactional_email
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, Http404
from django.urls import reverse
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q
from .models import Resume, JobDescription, ResumeInterviewSession, ResumeQuestion, ResumeAnswer, RazorpayPayment, InterviewViolation
from core.models import ScoreRecord
from jobs_app.models import JobPosting
from .resume_utils import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_doc,
    analyze_resume_with_sarvam,
    generate_interview_questions,
    evaluate_answer,
    extract_experience_years,
    validate_resume_fields
)

logger = logging.getLogger(__name__)


def _get_matched_jobs(matching_skills, years_experience=0.0, max_results=6):
    """
    Return active JobPostings filtered strictly by experience level
    and ranked by matching skills overlap.
    Rule: A fresher (< 1 year experience) must NOT receive Senior/Lead job postings (e.g. 5-8, 8+).
    Pass max_results=None for no cap (Pro plan gets unlimited recommendations).
    """
    def _cap(seq):
        return list(seq) if max_results is None else list(seq[:max_results])

    # A posting whose application deadline has passed is no longer
    # recommended (the deadline day itself still counts as open). Postings
    # without a deadline stay open until the employer closes them.
    base_qs = (
        JobPosting.objects.filter(status='active')
        .filter(Q(deadline__isnull=True) | Q(deadline__gte=timezone.localdate()))
        .select_related('employer')
    )

    # Strict Experience Level Filtering:
    # experience choices: ('fresher', 'Fresher'), ('1-2', '1-2 Years'), ('3-5', '3-5 Years'), ('5-8', '5-8 Years'), ('8+', '8+ Years')
    # Postings with a manually entered requirement ('custom') carry the exact
    # years in experience_years and are matched to the same bands.
    if years_experience <= 1.0:
        # Fresher / Entry level: Only allow fresher or 1-2 year roles
        base_qs = base_qs.filter(
            Q(experience__in=['fresher', '1-2'])
            | Q(experience='custom', experience_years__lte=2))
    elif years_experience <= 3.0:
        # Junior / Mid: allow fresher, 1-2, 3-5 roles
        base_qs = base_qs.filter(
            Q(experience__in=['fresher', '1-2', '3-5'])
            | Q(experience='custom', experience_years__lte=5))
    elif years_experience <= 5.0:
        # Mid / Experienced: allow 1-2, 3-5, 5-8 roles
        base_qs = base_qs.filter(
            Q(experience__in=['1-2', '3-5', '5-8'])
            | Q(experience='custom', experience_years__gte=1, experience_years__lte=8))
    else:
        # Senior: allow 3-5, 5-8, 8+ roles
        base_qs = base_qs.filter(
            Q(experience__in=['3-5', '5-8', '8+'])
            | Q(experience='custom', experience_years__gte=3))

    if matching_skills:
        skills = []
        for s in matching_skills:
            s = (s or '').strip()
            if s and s.lower() not in skills:
                skills.append(s.lower())

        if skills:
            skill_q = reduce(or_, [Q(skills_required__icontains=s) for s in skills])
            candidates = base_qs.filter(skill_q)

            def overlap_count(job):
                job_skills = job.skills_required.lower()
                return sum(1 for s in skills if s in job_skills)

            ranked = sorted(
                candidates,
                key=lambda j: (overlap_count(j), j.created_at),
                reverse=True,
            )
            
            if ranked:
                if max_results is not None and len(ranked) < max_results:
                    ranked_ids = [j.id for j in ranked]
                    others = base_qs.exclude(id__in=ranked_ids).order_by('-created_at')
                    ranked.extend(list(others[:max_results - len(ranked)]))
                elif max_results is None and len(ranked) < 5:
                    # If unlimited but we want to show at least 5
                    ranked_ids = [j.id for j in ranked]
                    others = base_qs.exclude(id__in=ranked_ids).order_by('-created_at')
                    ranked.extend(list(others[:5 - len(ranked)]))
                return _cap(ranked)

    return _cap(base_qs.order_by('-created_at'))


from django.contrib import messages
from users.models import UserProfile


def _get_user_plan(user):
    if not user.is_authenticated:
        return 'free'
    if user.is_superuser or user.is_staff:
        return 'pro'
    profile = getattr(user, 'profile', None)
    if not profile:
        return 'free'
    # Auto-revert a lapsed paid plan to Free before resolving entitlement, so an
    # expired subscription can never keep unlocking paid features.
    profile.enforce_expiry()
    # plan_type is the single source of truth. is_pro is a derived mirror kept in
    # sync by _activate_plan()/enforce_expiry() for templates; honouring it here
    # as well used to grant permanent Pro to any profile with the flag set but no
    # paid plan behind it — a state no expiry check could ever revoke.
    return getattr(profile, 'plan_type', 'free') or 'free'


def _can_access_interview(user):
    # AI Mock Interview, its results page and the score-gated job
    # recommendations: included from the Normal (₹499) plan upwards.
    return _get_user_plan(user) in ('normal', 'pro')


# How many job opportunities a passing candidate is shown, per plan.
# None means unlimited (Pro ₹999).
JOB_RECOMMENDATION_LIMITS = {'normal': 5, 'pro': None}


def _job_recommendation_limit(user):
    return JOB_RECOMMENDATION_LIMITS.get(_get_user_plan(user), 5)


# Days before expiry in which renewal is offered. Matches the 7-day reminder in
# career_app/context_processors.py — the notice and the button must agree.
RENEWAL_WINDOW_DAYS = 7


def _can_access_resume(user):
    # Resume Parsing / ATS Score Analysis is available on every plan, including
    # Free. The AI Technical Interview and its job recommendations are gated
    # separately by _can_access_interview() (Normal ₹499 and Pro).
    return user.is_authenticated


# Free plan: Resume Parsing / ATS analysis is capped at this many analyses in
# total (every analysis — fresh upload or re-analyze — creates one
# JobDescription row, so that row count is the usage counter).
FREE_RESUME_PARSE_LIMIT = 4


def _resume_parses_left(user):
    """Analyses a Free user still has; None means unlimited (paid plans)."""
    if _get_user_plan(user) != 'free':
        return None
    used = JobDescription.objects.filter(user=user).count()
    return max(0, FREE_RESUME_PARSE_LIMIT - used)


# The AI interview opens only for a resume whose ATS score reaches this.
ATS_INTERVIEW_THRESHOLD = 90


def _ats_unlocks_interview(analysis):
    try:
        return int((analysis or {}).get('match_percentage') or 0) >= ATS_INTERVIEW_THRESHOLD
    except (TypeError, ValueError, AttributeError):
        return False


def _slug(text):
    # Same slug as the Skill Up hub and landing page: "Oil & Gas" -> "oil-gas".
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def _remember_target_role(request):
    """Keep the role picked on the career-path page (?role=&dept=&track=) so a
    failed interview can send the user to that role's Skill Up content."""
    role = (request.GET.get('role') or '').strip()[:120]
    dept = (request.GET.get('dept') or '').strip()[:120]
    if not (_slug(role) and _slug(dept)):
        return
    track = 'nonit' if request.GET.get('track') == 'nonit' else 'tech'
    request.session['rb_role'] = {
        'role': role,
        'dept': dept,
        'track': track,
        # riya_bot.skillup_views only accepts role-<track>-<150 chars max>
        'section': f"role-{track}-{_slug(dept)}--{_slug(role)}"[:len(f"role-{track}-") + 150],
    }


def _check_role_fit(request, resume_text):
    """Judge the analysed resume against the target role (if one was picked)
    and keep the verdict for resume_start_interview. None without a role."""
    target = request.session.get('rb_role')
    if not target:
        request.session.pop('rb_role_fit', None)
        return None
    from .role_fit import assess_role_fit
    fit = assess_role_fit(resume_text, target.get('track', 'tech'), target['dept'], target['role'])
    request.session['rb_role_fit'] = fit
    analysis = request.session.get('rb_analysis')
    if fit['known'] and not fit['ok'] and isinstance(analysis, dict):
        # A resume that doesn't match the chosen role scores 0 for that role,
        # whatever the general ATS read said (it could show 100%). Same dict the
        # caller renders, so the result page and the session agree.
        analysis['match_percentage'] = 0
        # The AI summary judged the resume in general and may praise it; say why it scores 0 here.
        analysis['analysis'] = (
            f"This resume doesn't match the {target['role']} role ({target['dept']}). It doesn't show "
            f"the skills this role needs, so its ATS score for {target['role']} is 0%. Upload a resume "
            f"written for {target['role']}, or build one for this role."
        )
        request.session.modified = True
    return fit


def _skillup_url_for(request):
    target = request.session.get('rb_role') or {}
    url = reverse('skill_up')
    return f"{url}?section={target['section']}" if target.get('section') else url


def has_parsed_resume(user):
    from core.models import Resume
    return Resume.objects.filter(user=user).exclude(extracted_text='').exists()


@login_required
def pro_page(request):
    """Renders the Free vs Normal vs Pro user subscription plan comparison page."""
    current_plan = _get_user_plan(request.user)
    profile = getattr(request.user, 'profile', None)
    subscription_active = profile.is_subscription_active() if profile else False
    subscription_expiry = profile.subscription_expiry() if profile else None

    # Renewal is offered only in the last week of an active plan — the same
    # window that raises the "your plan expires soon" notice, so the notice's
    # call to action lands on a page that can act on it. Outside that week the
    # current-plan card stays clean.
    days_left = profile.days_until_expiry() if profile else None
    renewal_window = bool(subscription_active and days_left is not None and 0 <= days_left <= RENEWAL_WINDOW_DAYS)

    return render(request, "pro.html", {
        "current_plan": current_plan,
        "subscription_active": subscription_active,
        "subscription_expiry": subscription_expiry,
        "renewal_window": renewal_window,
        "days_left": days_left,
    })


@login_required
@require_POST
def toggle_pro_status(request):
    """Downgrade to the Free plan (no payment). Paid plans must go through Razorpay."""
    target_plan = request.POST.get("plan_type", "free").lower().strip()
    if target_plan != 'free':
        # Normal / Pro are paid — they must be purchased via Razorpay checkout.
        return redirect("pro_page")

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    # Block downgrade while a paid subscription is still within its 1-year window.
    if not profile.can_downgrade_to_free():
        expiry = profile.subscription_expiry()
        expiry_str = expiry.strftime("%d %b %Y") if expiry else "your plan's end date"
        messages.error(
            request,
            f"Your current paid plan is active until {expiry_str}. "
            "You can switch to the Free Plan only after it expires."
        )
        return redirect("pro_page")

    profile.plan_type = 'free'
    profile.is_pro = False
    profile.subscription_start = None
    # Scope the write: UserProfile carries the whole candidate record, and a full
    # save here would push back every stale field this instance was loaded with,
    # silently reverting a profile edit or resume upload saved a moment earlier.
    profile.save(update_fields=['plan_type', 'is_pro', 'subscription_start'])
    messages.info(request, "You are now on the Free Plan (₹0/yr).")
    return redirect("pro_page")


# ── Razorpay payment (TEST mode) ──────────────────────────────────────────────
# Prices are the base plan amounts; 18% GST is added on top, matching the
# "+ GST" shown on the pricing page. Amounts are charged in paise.
PLAN_PRICING = {
    'normal': {'base': 499, 'label': 'Normal User Plan (1 Year)'},
    'pro':    {'base': 999, 'label': 'Pro User Plan (1 Year)'},
}
GST_RATE = 0.18

# Checkout openings allowed per user per minute (PAY-P06).
ORDER_RATE_LIMIT_PER_MINUTE = 10

# Plan hierarchy: higher rank = higher tier. A user may never purchase a plan
# whose rank is lower than their current active plan's rank. Buying the SAME
# tier again is a renewal and is allowed — see _activate_plan().
PLAN_RANK = {'free': 0, 'normal': 1, 'pro': 2}


def _is_plan_downgrade(current_plan: str, target_plan: str) -> bool:
    """Return True when target_plan is a strictly lower tier than current_plan."""
    return PLAN_RANK.get(target_plan, 0) < PLAN_RANK.get(current_plan, 0)


def _activate_plan(profile, plan):
    """Put `plan` live on `profile`.

    Renewing the tier the user is already on stacks the new year on top of the
    time they have left, so paying early never burns the remaining days. Any
    other activation (first purchase, upgrade, purchase after a lapse) starts a
    fresh 1-year window from now.
    """
    if profile.is_subscription_active() and profile.plan_type == plan:
        # Same-tier renewal: time already paid for is carried over, so the new
        # year begins when the current term would have ended.
        profile.subscription_start = profile.subscription_expiry()
    else:
        # Upgrade (or first purchase, or purchase after a lapse): the old plan
        # is retired outright and the new tier's year starts from now. Carrying
        # over leftover time from a lower tier would silently stack two years'
        # worth of validity onto one purchase.
        profile.subscription_start = timezone.now()
    profile.plan_type = plan
    profile.is_pro = (plan == 'pro')
    # Only the subscription columns — a full save would write back every other
    # field as this instance saw it, clobbering concurrent profile updates.
    profile.save(update_fields=['plan_type', 'is_pro', 'subscription_start'])


def _revoke_subscription_year(profile):
    """Take one paid year back off a subscription after a refund settles.

    Pulling `subscription_start` back by the plan duration is what makes this
    correct for a stacked subscription: a customer who renewed twice and had one
    payment refunded keeps the year they still paid for, while a single refunded
    payment lands the expiry in the past and enforce_expiry() lapses them to Free
    on the next plan resolution.
    """
    from datetime import timedelta

    if profile.plan_type == 'free' or not profile.subscription_start:
        return
    profile.subscription_start -= timedelta(days=UserProfile.SUBSCRIPTION_DURATION_DAYS)
    profile.save(update_fields=['subscription_start'])
    profile.enforce_expiry()


def _handle_refund_event(payload):
    """PAY-P02: a refunded customer must not keep the plan they were refunded for.

    Razorpay reports refunds on their own events; without handling them the
    ledger cannot distinguish a refunded payment from a good one and nothing
    revokes the entitlement.
    """
    refund = ((payload.get('payload') or {}).get('refund') or {}).get('entity') or {}
    payment_id = refund.get('payment_id') or ''
    refund_amount = refund.get('amount')

    try:
        payment = RazorpayPayment.objects.select_related('user').get(razorpay_payment_id=payment_id)
    except RazorpayPayment.DoesNotExist:
        logger.warning(f'Razorpay refund for unknown payment {payment_id} — nothing to revoke.')
        return JsonResponse({'status': 'unknown_payment'})

    if payment.status == RazorpayPayment.STATUS_REFUNDED:
        return JsonResponse({'status': 'already_refunded'})

    total_refunded = (refund_amount if isinstance(refund_amount, int) else 0)
    is_full_refund = total_refunded >= payment.amount_paise

    # A payment that was captured but never applied bought no entitlement, so
    # there is nothing to take back — only the ledger entry to settle.
    was_applied = payment.status != RazorpayPayment.STATUS_REFUND_REQUIRED

    with transaction.atomic():  # type: ignore[attr-defined]
        payment.refunded_amount_paise = total_refunded
        payment.status = (RazorpayPayment.STATUS_REFUNDED if is_full_refund
                          else RazorpayPayment.STATUS_PARTIALLY_REFUNDED)
        payment.save(update_fields=['refunded_amount_paise', 'status', 'updated_at'])

        if is_full_refund and was_applied:
            profile, _ = UserProfile.objects.get_or_create(user=payment.user)
            _revoke_subscription_year(profile)

    if is_full_refund:
        logger.warning(
            f'Refund settled for payment {payment_id} (user {payment.user_id}) — '
            f'{"one subscription year revoked" if was_applied else "payment was never applied"}.'
        )
    else:
        # Partial refunds are a commercial decision, not an automatic revocation.
        logger.warning(
            f'PARTIAL REFUND recorded for payment {payment_id} (user {payment.user_id}): '
            f'{total_refunded} of {payment.amount_paise} paise. Entitlement left untouched — review manually.'
        )
    return JsonResponse({'status': 'refund_recorded', 'full_refund': is_full_refund})


def _send_payment_receipt(user, plan, payment_id, amount_paise, expiry, invoice_number=None, invoice_url=None):
    """Email the user their receipt after a successful payment.

    Called from both activation paths (browser callback and webhook), whichever
    one wins the idempotency check — so exactly one receipt goes out per
    payment. A mail failure is logged and swallowed: the money is already taken
    and the plan is already live, so a dead SMTP server must never turn a
    successful payment into an error for the user.
    """
    to_address = (getattr(user, 'email', '') or '').strip()
    if not to_address:
        logger.info(f'User {user.id} has no email on record — receipt for {payment_id} not sent.')
        return

    plan_label = PLAN_PRICING[plan]['label']
    # Split what was actually charged rather than quoting the current price list,
    # so a receipt for an order placed at an older price still adds up.
    total_amount = amount_paise / 100
    base_amount = total_amount / (1 + GST_RATE)
    context = {
        'user_name': user.get_full_name() or user.username,
        'plan_label': plan_label,
        'payment_id': payment_id,
        'base_amount': f'{base_amount:.2f}',
        'gst_amount': f'{total_amount - base_amount:.2f}',
        'total_amount': f'{total_amount:.2f}',
        'expiry': expiry,
        'paid_on': timezone.now(),
        'invoice_number': invoice_number,
        'invoice_url': invoice_url,
    }
    try:
        # send_transactional_email already swallows normal SMTP/template
        # failures internally and returns False; this outer try/except exists
        # so that even an unexpected bug in the mail path can never turn an
        # already-successful, already-captured payment into an error response.
        sent = send_transactional_email(
            subject=f'Payment received — {plan_label}',
            to_email=to_address,
            template_name='emails/payment_receipt.html',
            context=context,
        )
    except Exception as e:
        sent = False
        logger.exception(f'Could not send payment receipt for {payment_id}: {e}')

    if sent:
        logger.info(f'Payment receipt for {payment_id} emailed to user {user.id}.')
    else:
        logger.error(f'Could not send payment receipt for {payment_id} to user {user.id}.')


@login_required
def payment_invoice(request, pk):
    """Render the GST tax invoice for one payment.

    Fills the §34.3 gap where GST was charged but no invoice was produced.
    Viewable only by the payment's owner (or staff), so one guessed id cannot
    expose another customer's billing details. The page is print-ready — the
    customer saves it as a PDF from the browser.
    """
    payment = get_object_or_404(RazorpayPayment, pk=pk)
    if payment.user_id != request.user.id and not request.user.is_staff:
        raise Http404('Invoice not found.')

    # An older payment recorded before invoice numbering existed still gets a
    # stable number the first time its invoice is opened.
    if not payment.invoice_number:
        payment.assign_invoice_number()

    plan_label = PLAN_PRICING.get(payment.plan_type, {}).get('label', payment.plan_type)
    context = {
        'payment': payment,
        'plan_label': plan_label,
        'seller': {
            'name': settings.COMPANY_LEGAL_NAME,
            'gstin': settings.COMPANY_GSTIN,
            'address': settings.COMPANY_ADDRESS,
            'state': settings.COMPANY_STATE,
            'state_code': settings.COMPANY_STATE_CODE,
            'email': settings.COMPANY_EMAIL,
            'sac_code': settings.COMPANY_SAC_CODE,
        },
        'buyer': {
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
        },
        'gst_percent': round(getattr(settings, 'GST_RATE', 0.18) * 100),
        'half_gst_percent': round(getattr(settings, 'GST_RATE', 0.18) * 100) / 2,
    }
    return render(request, 'career_app/gst_invoice.html', context)

def _razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _plan_amount_paise(plan):
    base = PLAN_PRICING[plan]['base']
    return round(base * (1 + GST_RATE) * 100)  # base + 18% GST, in paise


def _quoted_amount_paise(notes, plan):
    """The price this order was actually quoted at.

    Orders carry their amount in the server-set notes, so an order stays
    verifiable at the price it was created with even if PLAN_PRICING changes
    while the customer is still on the checkout screen. Orders created before
    that note existed fall back to the current price table.
    """
    _MISSING = object()
    quoted = (notes or {}).get('amount_paise', _MISSING)
    if quoted is _MISSING:
        return _plan_amount_paise(plan)
    try:
        return int(quoted)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _plan_amount_paise(plan)


@login_required
@require_POST
def create_razorpay_order(request):
    """Create a Razorpay order (TEST mode) for the chosen plan; returns checkout params."""
    plan = request.POST.get('plan_type', '').lower().strip()
    if plan not in PLAN_PRICING:
        return JsonResponse({'success': False, 'error': 'Invalid plan.'}, status=400)

    # PAY-P06: nobody legitimately opens more than a handful of checkouts a
    # minute. Unthrottled, a logged-in user can loop order creation, burning
    # Razorpay API quota and filling the dashboard with abandoned orders.
    throttle_key = f'rzp_order_rate:{request.user.id}'
    if cache.get(throttle_key, 0) >= ORDER_RATE_LIMIT_PER_MINUTE:
        logger.warning(f'Order creation throttled for user {request.user.id}.')
        return JsonResponse({
            'success': False,
            'error': 'Too many payment attempts. Please wait a minute and try again.',
        }, status=429)
    try:
        cache.incr(throttle_key)
    except ValueError:
        cache.set(throttle_key, 1, 60)

    # Block downgrades while an active subscription exists (renewals are fine).
    current_plan = _get_user_plan(request.user)
    profile = getattr(request.user, 'profile', None)
    if profile and profile.is_subscription_active() and _is_plan_downgrade(current_plan, plan):
        return JsonResponse({
            'success': False,
            'error': f'You are on the {current_plan.capitalize()} Plan. '
                     'Switching to a lower plan is not allowed while your subscription is active.',
        }, status=400)

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return JsonResponse({'success': False, 'error': 'Payment is not configured.'}, status=500)

    amount = _plan_amount_paise(plan)
    try:
        client = _razorpay_client()
        order = client.order.create({
            'amount': amount,
            'currency': 'INR',
            # Unique per attempt — a fixed receipt made every attempt by the same
            # user for the same plan indistinguishable on the Razorpay side.
            'receipt': f'cb_{request.user.id}_{plan}_{uuid.uuid4().hex[:8]}',
            # amount_paise pins the price this order was quoted at. Verification
            # checks against it rather than recomputing from PLAN_PRICING, so
            # changing a price can't strand orders that are already in flight.
            'notes': {
                'user_id': str(request.user.id),
                'plan': plan,
                'amount_paise': str(amount),
            },
        })
    except razorpay.errors.BadRequestError as e:
        # The SDK drops the HTTP status; a rejected key pair surfaces as this
        # message. Logged distinctly so wrong/rotated keys aren't read as an outage.
        if 'authentication failed' in str(e).lower():
            logger.error('Razorpay rejected RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET — check .env.')
            return JsonResponse({'success': False, 'error': 'Payment is not configured.'}, status=401)
        logger.error(f'Razorpay order creation failed: {e}')
        return JsonResponse({'success': False, 'error': 'Could not start payment. Please try again.'}, status=502)
    except Exception as e:
        logger.error(f'Razorpay order creation failed: {e}')
        return JsonResponse({'success': False, 'error': 'Could not start payment. Please try again.'}, status=502)

    return JsonResponse({
        'success': True,
        'order_id': order['id'],
        'amount': amount,
        'currency': 'INR',
        'key_id': settings.RAZORPAY_KEY_ID,
        'plan_type': plan,
        'plan_label': PLAN_PRICING[plan]['label'],
        'user_name': request.user.get_full_name() or request.user.username,
        'user_email': request.user.email or '',
    })


@login_required
@require_POST
def verify_razorpay_payment(request):
    """Verify the Razorpay payment signature and activate the plan on success."""
    plan = request.POST.get('plan_type', '').lower().strip()
    payment_id = request.POST.get('razorpay_payment_id', '')
    order_id = request.POST.get('razorpay_order_id', '')
    signature = request.POST.get('razorpay_signature', '')

    # PAY-P12: the client's plan_type is deliberately NOT gated here. It is
    # overwritten further down by the plan recorded on the server-created order,
    # so validating it early protects nothing — it only throws away genuine
    # captures when the browser posts a mangled field, leaving the customer
    # charged with no record written.
    if not (payment_id and order_id and signature):
        return JsonResponse({'success': False, 'error': 'Missing payment details.'}, status=400)

    try:
        client = _razorpay_client()
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature,
        })
    except Exception as e:
        logger.warning(f'Razorpay signature verification failed: {e}')
        return JsonResponse({'success': False, 'error': 'Payment verification failed.'}, status=400)

    # BUG-02 fix: Reject replayed payment_ids — each payment may only activate a plan once.
    if RazorpayPayment.objects.filter(razorpay_payment_id=payment_id).exists():
        logger.warning(f'Duplicate Razorpay payment replay attempt: {payment_id} by user {request.user.id}')
        return JsonResponse({'success': False, 'error': 'This payment has already been used.'}, status=400)

    # PAY-01 fix (privilege-escalation): a valid signature only proves that
    # (order_id, payment_id) are genuine — it does NOT prove the order was for
    # the plan the browser posted. Without this check a user could pay for the
    # ₹499 Normal order and then POST plan_type='pro' with those same genuine
    # credentials to unlock Pro for the cheaper price. Re-fetch the order from
    # Razorpay and trust ONLY its server-set notes and amount.
    try:
        order = client.order.fetch(order_id)
    except Exception as e:
        # The signature already proved this payment is genuine, so the money is
        # captured — this is Razorpay being unreachable, not a bad payment.
        # Saying "verification failed" would read as a lost payment; report it as
        # pending instead and let the webhook finish the activation.
        logger.error(f'Razorpay order fetch failed for {order_id} (payment {payment_id}): {e}')
        return JsonResponse({
            'success': False,
            'pending': True,
            'error': 'Your payment went through, but we could not confirm it just now. '
                     'It will activate automatically within a few minutes.',
        })

    order_notes  = order.get('notes') or {}
    order_plan   = (order_notes.get('plan') or '').lower().strip()
    order_user   = str(order_notes.get('user_id') or '')
    order_amount = order.get('amount')

    # Ownership is checked before anything else that could write a ledger row:
    # only once we know the money belongs to this user may we record it against
    # them. A payment on someone else's order is not our customer's money.
    if order_user != str(request.user.id):
        logger.warning(f'Order {order_id} ownership mismatch: notes={order_user} auth={request.user.id}')
        return JsonResponse({'success': False, 'error': 'Payment verification failed.'}, status=400)

    def _record_unapplied(reason):
        """The signature and the owner check both passed, so this capture is real
        money belonging to this user. Whatever is wrong is on our side, so the
        payment has to reach the ledger — otherwise it is invisible to support
        and impossible to reconcile against Razorpay or refund."""
        RazorpayPayment.objects.get_or_create(
            razorpay_payment_id=payment_id,
            defaults={
                'user': request.user,
                'razorpay_order_id': order_id,
                'plan_type': (order_plan or 'unknown')[:20],
                'amount_paise': order_amount or 0,
                'currency': (order.get('currency') or 'INR')[:8],
                'status': RazorpayPayment.STATUS_REFUND_REQUIRED,
            },
        )
        logger.warning(f'REFUND REQUIRED: captured payment {payment_id} for user '
                       f'{request.user.id} could not be applied — {reason}')

    # Only INR orders are ever created here; anything else means the amount below
    # would be compared against a different currency's minor units.
    if (order.get('currency') or 'INR') != 'INR':
        _record_unapplied(f'order currency is {order.get("currency")!r}, not INR')
        return JsonResponse({'success': False, 'error': 'Payment verification failed.'}, status=400)

    # PAY-P04: a valid signature proves the payment is genuine, not that the money
    # was captured. Under manual capture an authorised-but-uncaptured payment
    # would otherwise activate a plan against money that never settles. Reported
    # as pending rather than failed: with automatic capture the order can still be
    # a moment behind the callback, and the webhook completes the activation.
    order_status = (order.get('status') or '').lower()
    if order_status and order_status != 'paid':
        logger.warning(f'Order {order_id} is not paid yet: {order_status!r} (payment {payment_id}).')
        return JsonResponse({
            'success': False,
            'pending': True,
            'error': 'Your payment is still being confirmed by the bank. '
                     'Your plan will activate automatically once it settles.',
        })

    # Authoritative plan is the one the order was CREATED for — never the client POST.
    if order_plan not in PLAN_PRICING:
        _record_unapplied(f'order carries an invalid plan note: {order_plan!r}')
        return JsonResponse({'success': False, 'error': 'Payment verification failed.'}, status=400)

    # Paid amount must equal the price this order was quoted at (guards tampered orders).
    expected_amount = _quoted_amount_paise(order_notes, order_plan)
    if order_amount != expected_amount:
        _record_unapplied(f'amount mismatch: paid={order_amount} expected={expected_amount}')
        return JsonResponse({'success': False, 'error': 'Payment verification failed.'}, status=400)

    # From here on, trust the order — discard any client-supplied plan value.
    plan = order_plan

    # Final server-side rank check before activating.
    current_plan = _get_user_plan(request.user)
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if profile.is_subscription_active() and _is_plan_downgrade(current_plan, plan):
        # Reachable with two orders open at once: buy Normal and Pro in separate
        # tabs while on Free, pay both, and Pro lands first. The money for this
        # one is already captured, so record it before refusing — an unrecorded
        # capture is invisible in the admin ledger and impossible to reconcile
        # against Razorpay when the user asks where their money went.
        RazorpayPayment.objects.get_or_create(
            razorpay_payment_id=payment_id,
            defaults={
                'user': request.user,
                'razorpay_order_id': order_id,
                'plan_type': plan,
                'amount_paise': order_amount,
                # PAY-P08: the ledger, not just the log, carries the fact that
                # money is owed back — support can filter for it in the admin.
                'status': RazorpayPayment.STATUS_REFUND_REQUIRED,
            },
        )
        logger.warning(
            f'REFUND REQUIRED: captured payment {payment_id} for {plan} could not be applied — '
            f'user {request.user.id} is already on {current_plan}.'
        )
        return JsonResponse({
            'success': False,
            'error': f'You are on the {current_plan.capitalize()} Plan, so this '
                     f'{plan.capitalize()} payment could not be applied. It has been '
                     'recorded — please contact support to arrange a refund.',
        }, status=400)

    # PAY-03 fix: the unique constraint on razorpay_payment_id makes this the
    # atomic guard against two concurrent verify requests racing past the
    # exists() check above — the loser hits IntegrityError instead of an
    # unhandled 500.
    # One transaction: the payment record is what blocks a replay, so it must not
    # survive on its own if the activation beside it fails. Committed separately,
    # a failed activation would leave the payment marked as used — every retry
    # rejected as a replay, the webhook skipping it as already processed, and the
    # user left paid-up on the Free plan with no way back.
    try:
        with transaction.atomic():  # type: ignore[attr-defined]
            payment = RazorpayPayment.objects.create(
                user=request.user,
                razorpay_payment_id=payment_id,
                razorpay_order_id=order_id,
                plan_type=plan,
                amount_paise=order_amount,
            )
            payment.assign_invoice_number()
            _activate_plan(profile, plan)
    except IntegrityError:
        logger.warning(f'Concurrent replay of payment {payment_id} blocked by unique constraint.')
        return JsonResponse({'success': False, 'error': 'This payment has already been used.'}, status=400)
    invoice_url = request.build_absolute_uri(reverse('payment_invoice', args=[payment.pk]))
    _send_payment_receipt(
        request.user, plan, payment_id, order_amount, profile.subscription_expiry(),
        invoice_number=payment.invoice_number, invoice_url=invoice_url,
    )

    if plan == 'pro':
        messages.success(request, "🎉 Payment successful! Pro Plan is now active — Resume Parsing, AI Interview & Job Recommendations unlocked.")
    else:
        messages.success(request, "👍 Payment successful! Normal Plan is now active — Activities, Grammar, Dashboard & Resume Parsing unlocked.")
    return JsonResponse({'success': True, 'plan_type': plan})


@login_required
def resume_builder_home(request):
    """Renders the resume upload and analysis home page."""
    if not _can_access_resume(request.user):
        return render(request, "resume_locked.html")
    _remember_target_role(request)
    return render(request, "resume_builder.html", _builder_context(request))


def _builder_context(request, **extra):
    return {
        "target_role": request.session.get("rb_role"),
        "parses_left": _resume_parses_left(request.user),
        "parse_limit": FREE_RESUME_PARSE_LIMIT,
        **extra,
    }


def _parse_limit_reached(user):
    return _resume_parses_left(user) == 0


PARSE_LIMIT_MSG = (f"You have used all {FREE_RESUME_PARSE_LIMIT} Resume Parsing analyses included in the "
                   "Free plan. Upgrade your plan to keep analysing resumes and unlock the AI Interview.")

@login_required
def resume_job_match(request):
    """Handles resume + JD upload and runs AI analysis."""
    if not _can_access_resume(request.user):
        return redirect("resume_builder")
    if request.method == "POST":
        if _parse_limit_reached(request.user):
            return render(request, "resume_builder.html", _builder_context(request, error=PARSE_LIMIT_MSG))
        resume_file = request.FILES.get("file")
        jd_text = request.POST.get("text", "").strip()

        if not resume_file:
            return render(request, "resume_builder.html", _builder_context(request, error="Please upload a resume."))
        
        db_jd_text = jd_text if jd_text else "General Resume Analysis"
        resume = Resume.objects.create(user=request.user)
        resume.file.save(resume_file.name, resume_file)
        file_path = resume.file.path

        if resume_file.name.lower().endswith(".pdf"):
            extracted_text = extract_text_from_pdf(file_path)
        elif resume_file.name.lower().endswith(".docx"):
            extracted_text = extract_text_from_docx(file_path)
        elif resume_file.name.lower().endswith(".doc"):
            extracted_text = extract_text_from_doc(file_path)
        else:
            # Read the just-saved copy from disk rather than the original
            # upload stream: resume.file.save() above already consumed it by
            # iterating its chunks to write to storage, so re-reading
            # `resume_file` directly returned b'' for every plain-text
            # resume — every non-PDF/DOCX upload was rejected as unreadable
            # regardless of its actual content, unlike the PDF/DOCX branches
            # above, which already read from `file_path` and were unaffected.
            with open(file_path, "rb") as f:
                extracted_text = f.read().decode("utf-8", errors="ignore")

        clean_text = (extracted_text or "").strip()
        if not clean_text or clean_text.lower().startswith("error reading"):
            logger.error(f"Resume text extraction failed: {extracted_text!r}")
            resume.delete()
            if clean_text.lower().startswith("error reading"):
                msg = ("We couldn't open this file. Please make sure it is a valid, "
                       "non-password-protected PDF or DOCX and try again.")
            else:
                msg = ("We couldn't read any text from this resume. It looks like a "
                       "scanned or image-based file. Please upload a text-based PDF or "
                       "DOCX (one you can select/copy text from).")
            return render(request, "resume_builder.html", _builder_context(request, error=msg))

        # Validate resume fields before proceeding
        is_valid, matched_count, matched_fields, missing_fields = validate_resume_fields(clean_text)
        
        resume_valid = is_valid
        validation_msg = ""
        if not is_valid:
            validation_msg = f"Invalid resume. We could only find {matched_count} out of 10 standard resume sections. Please ensure your resume contains at least 3 of: Name & Contact Info, Summary, Technical Skills, Work Experience, Projects, Education, Certifications, Achievements, Languages, or Additional Info."


        resume.extracted_text = clean_text
        resume.save()
        analysis = analyze_resume_with_sarvam(clean_text, jd_text)

        if isinstance(analysis, dict) and "error" in analysis:
            logger.error(f"AI Analysis Failed: {analysis['error']}")
            return render(request, "resume_builder.html", _builder_context(request, error=f"AI analysis failed: {analysis['error']}"))
        # Created only after a successful analysis: this row is what counts
        # against the Free plan's parse limit, so a failed attempt is free.
        jd = JobDescription.objects.create(user=request.user, text=db_jd_text)

        request.session["rb_resume_id"] = resume.id
        request.session["rb_jd_id"] = jd.id
        request.session["rb_analysis"] = analysis
        request.session["rb_interview_current_idx"] = 0
        request.session["rb_interview_session_id"] = None
        request.session.modified = True

        matching_skills = analysis.get('matching_skills', []) if isinstance(analysis, dict) else []
        years_exp = extract_experience_years(clean_text)
        role_fit = _check_role_fit(request, clean_text)

        return render(request, "resume_match_result.html", {
            "analysis": analysis,
            "resume": resume,
            "jd": jd,
            "is_ats_only": not jd_text,
            "years_exp": years_exp,
            "can_interview": _can_access_interview(request.user),
            "ats_ok": _ats_unlocks_interview(analysis),
            "ats_threshold": ATS_INTERVIEW_THRESHOLD,
            "role_fit": role_fit,
            "target_role": request.session.get("rb_role"),
            "resume_valid": resume_valid,
            "validation_msg": validation_msg,
        })

    analysis = request.session.get("rb_analysis")
    if analysis:
        res_id = request.session.get("rb_resume_id")
        years_exp = 0.0
        if res_id:
            try:
                res_obj = Resume.objects.get(id=res_id)
                years_exp = extract_experience_years(res_obj.extracted_text)
            except Resume.DoesNotExist:
                pass
        return render(request, "resume_match_result.html", {
            "analysis": analysis,
            "is_ats_only": True,
            "years_exp": years_exp,
            "can_interview": _can_access_interview(request.user),
            "ats_ok": _ats_unlocks_interview(analysis),
            "ats_threshold": ATS_INTERVIEW_THRESHOLD,
            "role_fit": request.session.get("rb_role_fit"),
            "target_role": request.session.get("rb_role"),
        })
    return redirect("resume_builder")


@login_required
def resume_history(request):
    """Lists every resume this user has ever uploaded.

    Each upload already creates its own Resume row (resume_job_match above
    never deletes or overwrites a previous one) — the only thing missing was
    a page to see them, since the upload flow only ever tracks the single
    most recent resume in the session (rb_resume_id). Past resumes were
    never lost, just inaccessible once a newer upload replaced that session
    value.
    """
    if not _can_access_resume(request.user):
        return render(request, "resume_locked.html")

    resumes = Resume.objects.filter(user=request.user).order_by("-uploaded_at")
    current_resume_id = request.session.get("rb_resume_id")

    return render(request, "resume_history.html", {
        "resumes": resumes,
        "current_resume_id": current_resume_id,
    })


@login_required
@require_POST
def resume_reanalyze(request, resume_id):
    """Re-runs ATS analysis on a previously uploaded resume from resume_history.

    Reuses the resume's already-stored extracted_text rather than re-parsing
    the file, and otherwise mirrors resume_job_match's success path (same
    session keys, same result template) so "Try Interview" and everything
    else on that page behaves identically to a fresh upload.
    """
    if not _can_access_resume(request.user):
        return redirect("resume_builder")

    if _parse_limit_reached(request.user):
        messages.error(request, PARSE_LIMIT_MSG)
        return redirect("resume_history")

    resume = get_object_or_404(Resume, id=resume_id, user=request.user)
    if not resume.extracted_text:
        messages.error(request, "This resume has no readable text saved — please upload it again.")
        return redirect("resume_history")

    analysis = analyze_resume_with_sarvam(resume.extracted_text, "")
    if isinstance(analysis, dict) and "error" in analysis:
        logger.error(f"AI Analysis Failed (re-analyze): {analysis['error']}")
        messages.error(request, f"AI analysis failed: {analysis['error']}")
        return redirect("resume_history")

    jd = JobDescription.objects.create(user=request.user, text="General Resume Analysis")

    request.session["rb_resume_id"] = resume.id
    request.session["rb_jd_id"] = jd.id
    request.session["rb_analysis"] = analysis
    request.session["rb_interview_current_idx"] = 0
    request.session["rb_interview_session_id"] = None
    request.session.modified = True

    years_exp = extract_experience_years(resume.extracted_text)
    role_fit = _check_role_fit(request, resume.extracted_text)

    from career_app.resume_utils import validate_resume_fields
    is_valid, matched_count, matched_fields, missing_fields = validate_resume_fields(resume.extracted_text)
    
    resume_valid = is_valid
    validation_msg = ""
    if not is_valid:
        validation_msg = f"Invalid resume. We could only find {matched_count} out of 10 standard resume sections. Please ensure your resume contains at least 3 of: Name & Contact Info, Summary, Technical Skills, Work Experience, Projects, Education, Certifications, Achievements, Languages, or Additional Info."

    return render(request, "resume_match_result.html", {
        "analysis": analysis,
        "resume": resume,
        "jd": jd,
        "is_ats_only": True,
        "years_exp": years_exp,
        "can_interview": _can_access_interview(request.user),
        "ats_ok": _ats_unlocks_interview(analysis),
        "ats_threshold": ATS_INTERVIEW_THRESHOLD,
        "role_fit": role_fit,
        "target_role": request.session.get("rb_role"),
        "resume_valid": resume_valid,
        "validation_msg": validation_msg,
    })


def _ensure_resume_interview_questions(session):
    if session.questions.exists(): return
    skills = session.matching_skills or []
    # Pass the candidate through: generate_interview_questions() uses it to skip
    # questions they were already asked in earlier sessions, so a repeat
    # interview is a different paper. Without it every interview looked alike.
    #
    # domain_count=10: build ALL 20 questions (Behavioural + Experience +
    # Domain) up front, once, so every question — including the technical/
    # domain ones — is served instantly from a persisted row, exactly like the
    # behavioural/experience ones. Selecting domain questions live, one at a
    # time, added a slow per-question DB sample right before each was shown.
    raw_questions = generate_interview_questions(
        session.resume.extracted_text,
        session.job_description.text,
        skills=skills,
        user=getattr(session.resume, 'user', None),
        domain_count=10,
        focus=session.target_role,
    )
    for i, q_data in enumerate(raw_questions):

        ResumeQuestion.objects.create(
            session=session,
            question_text=q_data.get("question", ""),
            topic=q_data.get("topic", "General"),
            difficulty=q_data.get("difficulty", "Easy"),
            question_type=q_data.get("question_type", "theory"),

        order=i
    )

@login_required
def resume_start_interview(request):
    # AI Technical Interview is included from the Normal (₹499) plan upwards.
    if not _can_access_interview(request.user):
        messages.info(request, "AI Mock Interview is available only on Premium plans. Your Free plan includes AI Resume Parsing and ATS Resume Score. Please upgrade your plan to access AI Mock Interview.")
        return redirect("pro_page")
    if not has_parsed_resume(request.user):
        messages.info(request, "Please parse your resume first to access AI Mock Interview.")
        return redirect("resume_builder")
        
    res_id, jd_id = request.session.get("rb_resume_id"), request.session.get("rb_jd_id")
    analysis = request.session.get("rb_analysis", {})
    if not res_id or not jd_id: return redirect("resume_job_match")
    if not _ats_unlocks_interview(analysis):
        messages.info(request, f"The AI Interview unlocks when your resume's ATS score is {ATS_INTERVIEW_THRESHOLD}% or higher. Improve your resume and analyse it again.")
        return redirect("resume_job_match")
    target, fit = request.session.get("rb_role"), request.session.get("rb_role_fit")
    if target and fit and not fit.get("ok"):
        messages.info(request, f"This resume does not match the {target['role']} role you picked, so the AI Interview for that role is locked. Upload a resume for {target['role']}, or pick the role that fits this resume.")
        return redirect("resume_job_match")
    
    resume = Resume.objects.get(id=res_id, user=request.user)
    jd = JobDescription.objects.get(id=jd_id, user=request.user)
    from career_app.resume_utils import extract_experience_years, classify_experience_level
    years = extract_experience_years(resume.extracted_text)
    experience_level = classify_experience_level(years)
    interview_session = ResumeInterviewSession.objects.create(
        resume=resume, job_description=jd,
        matching_skills=analysis.get("matching_skills", []),
        experience_level=experience_level,
        # Domain questions follow the chosen role (see resume_utils._domain_inputs).
        target_role=(
            {**target, 'text': fit['text'], 'topics': fit.get('topics') or [], 'industries': fit['industries']}
            if target and fit and fit.get('known') else None
        ),
    )
    
    request.session["rb_interview_session_id"] = interview_session.id
    request.session["rb_interview_current_idx"] = 0
    request.session.modified = True
    return redirect("resume_interview_chat")

@login_required
def resume_interview_chat(request):
    if not _can_access_interview(request.user):
        messages.info(request, "AI Mock Interview is available only on Premium plans. Your Free plan includes AI Resume Parsing and ATS Resume Score. Please upgrade your plan to access AI Mock Interview.")
        return redirect("pro_page")
    if not has_parsed_resume(request.user):
        messages.info(request, "Please parse your resume first to access AI Mock Interview.")
        return redirect("resume_builder")
        
    s_id = request.session.get("rb_interview_session_id")
    if not s_id: return redirect("resume_job_match")
    session = ResumeInterviewSession.objects.get(id=s_id)
    _ensure_resume_interview_questions(session)
    return render(request, "resume_interview.html")

# Interview score that unlocks job recommendations (inclusive).
PASSING_SCORE = 90

ANSWER_TIME_LIMIT_SECONDS = 30
# Grace covers only the auto-submit's own network round trip, not extra
# thinking time past the 30s limit.
ANSWER_TIME_GRACE_SECONDS = 10


def _save_timeout_answer(question, user):
    """Finalizes a question nobody answered in time (e.g. abandoned via a page
    refresh) as a timed-out zero-score answer, so the 30s limit can't be
    dodged by never calling resume_submit_answer at all."""
    ResumeAnswer.objects.update_or_create(
        question=question,
        defaults={
            "text": "",
            "score": 0,
            "feedback": "No answer was submitted within the time limit.",
            "timed_out": True,
        },
    )
    ScoreRecord.objects.create(user=user, module="interview", score=0, max_score=5, label=question.topic)


def _score_and_finalize_session(session):
    """Computes and stores this session's final score using the same
    formula as resume_analytics (each question worth 5 marks, scaled to a
    0-100 integer), so total_score/is_passed reflect the real result the
    moment the interview ends — before resume_upload_interview_video (called
    right after) has to decide whether to keep or discard the recording.
    """
    questions = list(session.questions.all().order_by("order"))
    total_questions = len(questions)
    total_raw_score = 0
    answered_count = 0   # questions the candidate actually reached (answered OR timed-out)
    for q in questions:
        try:
            total_raw_score += (q.answer.score or 0)
            answered_count += 1
        except ResumeAnswer.DoesNotExist:
            # Never reached — the candidate stopped before this question.
            pass

    # Fair partial scoring: an honest candidate who stops midway is scored only
    # on the questions they actually reached, not out of the full 20 (which would
    # count every un-served question as 0/5 and crush the result). A malpractice
    # termination is different — the interview was force-ended for cheating, so
    # the unanswered questions stay as zeros against the full paper.
    terminated = session.malpractice_status == ResumeInterviewSession.MALPRACTICE_TERMINATED
    denom_questions = total_questions if terminated else answered_count
    max_possible_raw = (denom_questions * 5) if denom_questions > 0 else 0
    scaled_percentage = (total_raw_score / max_possible_raw * 100) if max_possible_raw > 0 else 0
    total_integer_score = min(100, math.ceil(scaled_percentage))
    session.total_score = total_integer_score
    session.is_passed = total_integer_score >= PASSING_SCORE
    session.save(update_fields=["is_completed", "total_score", "is_passed"])


@login_required
@require_POST
def resume_camera_verified(request):
    """Marks this interview session's camera as verified, server-side.

    Called by the JS camera-gate screen the moment it confirms a live video
    track, right before the interview UI is revealed. resume_get_next_question
    and resume_submit_answer both require this to be set, so the mandatory
    camera requirement is enforced in application logic — not only by the
    frontend gate — without touching question, scoring, or audio behaviour.
    """
    s_id = request.session.get("rb_interview_session_id")
    if not s_id:
        return JsonResponse({"error": "No session"}, status=400)
    session = get_object_or_404(ResumeInterviewSession, id=s_id, resume__user=request.user)
    session.camera_verified_at = timezone.now()
    session.save(update_fields=["camera_verified_at"])
    return JsonResponse({"ok": True})


MALPRACTICE_FLAG_THRESHOLD = 2     # this many total violations -> flagged for review
MALPRACTICE_TERMINATE_THRESHOLD = 3  # 3-strike rule: 3rd violation force-ends the interview

ALLOWED_VIOLATION_TYPES = {choice[0] for choice in InterviewViolation.TYPE_CHOICES}


@login_required
@require_GET
def resume_violation_state(request):
    """Returns this session's current violation count/status, so a page
    refresh (or a second tab) restores the real server-side state instead of
    the frontend silently starting back at zero — the counter itself only
    ever lives in the DB (see resume_record_violation), this just reads it.
    """
    s_id = request.session.get("rb_interview_session_id")
    if not s_id:
        return JsonResponse({"error": "No session"}, status=400)
    session = get_object_or_404(ResumeInterviewSession, id=s_id, resume__user=request.user)
    return JsonResponse({
        "count": session.malpractice_violation_count,
        "status": session.malpractice_status,
        "flag_threshold": MALPRACTICE_FLAG_THRESHOLD,
        "terminate_threshold": MALPRACTICE_TERMINATE_THRESHOLD,
    })


@login_required
@require_POST
def resume_record_violation(request):
    """Records one anti-malpractice event and returns the escalation action.

    The count this decides on is always read fresh from the session row, so
    it can't be bypassed by refreshing, reloading in a new tab, or by the
    client claiming a different count — a violation always adds exactly 1 to
    whatever is already stored server-side.

    Escalation (per the spec's progressive-warning requirement): the first
    couple of violations are just a warning; MALPRACTICE_FLAG_THRESHOLD flags
    the session for manual review without stopping it; a genuinely repeated
    pattern past MALPRACTICE_TERMINATE_THRESHOLD force-ends the interview
    through the same completion/scoring path a normal finish uses (so
    scoring and the existing recording save/discard rule are untouched —
    only how the interview ended differs).
    """
    s_id = request.session.get("rb_interview_session_id")
    if not s_id:
        return JsonResponse({"error": "No session"}, status=400)
    session = get_object_or_404(ResumeInterviewSession, id=s_id, resume__user=request.user)

    violation_type = request.POST.get("type", "")
    if violation_type not in ALLOWED_VIOLATION_TYPES:
        return JsonResponse({"error": "Invalid violation type"}, status=400)

    if session.malpractice_status == ResumeInterviewSession.MALPRACTICE_TERMINATED:
        # Already ended for malpractice — nothing left to escalate.
        return JsonResponse({
            "count": session.malpractice_violation_count,
            "status": session.malpractice_status,
            "action": "terminated",
        })

    duration_seconds = request.POST.get("duration_seconds")
    try:
        duration_seconds = float(duration_seconds) if duration_seconds is not None else None
    except (TypeError, ValueError):
        duration_seconds = None

    type_occurrence_number = InterviewViolation.objects.filter(
        session=session, violation_type=violation_type
    ).count() + 1
    InterviewViolation.objects.create(
        session=session,
        violation_type=violation_type,
        occurrence_number=type_occurrence_number,
        duration_seconds=duration_seconds,
    )

    session.malpractice_violation_count += 1
    if session.malpractice_violation_count >= MALPRACTICE_TERMINATE_THRESHOLD:
        session.malpractice_status = ResumeInterviewSession.MALPRACTICE_TERMINATED
        action = "terminated"
    elif session.malpractice_violation_count >= MALPRACTICE_FLAG_THRESHOLD:
        session.malpractice_status = ResumeInterviewSession.MALPRACTICE_FLAGGED
        action = "flagged"
    else:
        action = "warn"
    session.save(update_fields=["malpractice_violation_count", "malpractice_status"])

    if action == "terminated":
        # End the interview the same way a normal completion does — this
        # scores whatever was actually answered so far and applies the
        # existing pass/fail recording rule unchanged; only the reason the
        # interview stopped (malpractice, not "ran out of questions") differs.
        session.is_completed = True
        _score_and_finalize_session(session)

    return JsonResponse({
        "count": session.malpractice_violation_count,
        "status": session.malpractice_status,
        "action": action,
        "type_occurrence_number": type_occurrence_number,
    })


@login_required
@require_POST
def resume_upload_interview_video(request):
    """Stores the continuous webcam recording captured for this interview —
    but only when the session's final score is a pass (>= PASSING_SCORE).

    The client always sends the recording it captured; the keep/discard
    decision is made here, server-side, from session.total_score/is_passed
    (already computed by _score_and_finalize_session at the moment the
    interview completed, just before this request). Below the threshold the
    uploaded video is simply never written to a FileField/disk — Django's
    request-scoped upload handling cleans up its temp storage on its own —
    so nothing below-passing ever reaches persistent storage.
    """
    s_id = request.session.get("rb_interview_session_id")
    if not s_id:
        return JsonResponse({"error": "No session"}, status=400)
    session = get_object_or_404(ResumeInterviewSession, id=s_id, resume__user=request.user)
    video = request.FILES.get("video")
    if not video:
        # Previously silent — a session that qualified to keep its recording
        # (is_passed=True) but never got a file here (client-side capture or
        # network failure) looked identical to one that simply never tried.
        # Logged only when it's actually worth knowing about: a pass with no
        # video is the case that matters for this feature's core guarantee.
        if session.is_completed and session.is_passed:
            logger.warning("resume_upload_interview_video: no video file received for passing session %s", session.id)
        return JsonResponse({"error": "No video uploaded"}, status=400)
    if not session.is_passed:
        return JsonResponse({"ok": True, "stored": False})
    session.interview_video = video
    session.save(update_fields=["interview_video"])
    return JsonResponse({"ok": True, "stored": True})


@login_required
@require_GET
def resume_get_next_question(request):
    s_id = request.session.get("rb_interview_session_id")
    if not s_id: return JsonResponse({"error": "No session"}, status=400)
    session = ResumeInterviewSession.objects.get(id=s_id)
    # Mandatory-camera enforcement, server-side: the frontend never calls
    # this until its own camera gate has passed, so for a legitimate session
    # camera_verified_at is already set by the time execution reaches here —
    # this only blocks a request that bypassed the gate entirely.
    if not session.camera_verified_at:
        return JsonResponse({
            "error": "camera_required",
            "message": "Camera access is required to attend the interview. Please allow camera access and try again.",
        }, status=403)
    if session.malpractice_status == ResumeInterviewSession.MALPRACTICE_TERMINATED:
        return JsonResponse({
            "error": "malpractice_terminated",
            "message": "This interview was ended due to repeated malpractice violations.",
        }, status=403)
    questions = list(session.questions.all().order_by("order"))
    curr_idx = request.session.get("rb_interview_current_idx", 0)

    if request.GET.get("next") == "true":
        if curr_idx < len(questions) and hasattr(questions[curr_idx], "answer"):
            curr_idx += 1
            request.session["rb_interview_current_idx"] = curr_idx
            request.session.modified = True

    # Domain questions (order 10-19) are selected one at a time, adapting
    # difficulty to how the candidate has actually scored so far, instead
    # of being generated all at once before the interview starts. This is
    # the point where that lazy selection happens - right when the
    # candidate reaches a slot that hasn't been created yet.
    if len(questions) <= curr_idx < 20:
        from career_app.resume_utils import next_domain_difficulty, select_next_domain_question
        difficulty = next_domain_difficulty(session)
        next_q = select_next_domain_question(session, difficulty)
        if next_q is not None:
            ResumeQuestion.objects.create(
                session=session,
                question_text=next_q.get("question", ""),
                topic=next_q.get("topic", "Domain"),
                difficulty=next_q.get("difficulty", difficulty),
                question_type=next_q.get("question_type", "theory"),
                order=curr_idx,
            )
            questions = list(session.questions.all().order_by("order"))
        # next_q is None only when truly nothing eligible remains anywhere
        # (bank exhausted for this candidate/role/difficulty combination).
        # Per the spec's safety-fallback rule, that ends the interview
        # rather than repeating a question or crashing.

    # Auto-finalize any question the user abandoned without submitting (e.g. by
    # refreshing the page instead of waiting out the 30s timer) as a timed-out
    # zero-score answer, then move past it — closes off using a refresh to
    # dodge the timer, since a stale question is skipped rather than re-served
    # with a fresh clock.
    while curr_idx < len(questions):
        q = questions[curr_idx]
        if hasattr(q, "answer") or not q.presented_at:
            break
        elapsed = (timezone.now() - q.presented_at).total_seconds()
        if elapsed <= ANSWER_TIME_LIMIT_SECONDS + ANSWER_TIME_GRACE_SECONDS:
            break
        _save_timeout_answer(q, request.user)
        curr_idx += 1
    request.session["rb_interview_current_idx"] = curr_idx
    request.session.modified = True

    if curr_idx >= len(questions):
        session.is_completed = True
        # Score the session now (not only later, on-demand, in resume_analytics)
        # so resume_upload_interview_video — called by the client immediately
        # after this "completed" response — already knows whether to keep or
        # discard the recording it's about to receive.
        _score_and_finalize_session(session)
        return JsonResponse({"status": "completed"})

    q = questions[curr_idx]
    if not q.presented_at:
        q.presented_at = timezone.now()
        q.save(update_fields=["presented_at"])
    elapsed = (timezone.now() - q.presented_at).total_seconds()
    time_remaining = max(0, int(ANSWER_TIME_LIMIT_SECONDS - elapsed))
    question_lower = q.question_text.lower()

    coding_keywords = [
        "write a query",
        "sql",
        "select",
        "insert",
        "update",
        "delete",
        "join",
        "group by",
        "order by",
        "having",
        "create table",
        "alter table",
        "drop table",
        "python",
        "java",
        "c++",
        "javascript",
        "write a program",
        "write code",
        "algorithm"
    ]

    is_coding = any(keyword in question_lower for keyword in coding_keywords)

    # The total questions in a full interview is fixed at 20 (5 Behavioural +
    # 5 Experience + 10 Domain) even though, since domain questions are now
    # created lazily one at a time, len(questions) only reflects how many
    # ResumeQuestion rows exist SO FAR - using it as the denominator here
    # showed a misleading "12/12 = 100%" partway through, because only 12 of
    # the eventual 20 had been created yet at that point.
    total_questions = max(len(questions), 20)

    return JsonResponse({
        "id": q.id,
        "text": q.question_text,
        "topic": q.topic,
        "difficulty": q.difficulty,
        "progress": f"{curr_idx+1}/{total_questions}",
        "status": "active",
        "is_coding": q.question_type == "coding",
"question_type": q.question_type,
        "time_limit": ANSWER_TIME_LIMIT_SECONDS,
        "time_remaining": time_remaining,
    })

@login_required
@require_POST
def resume_submit_answer(request):
    q_id = request.POST.get("question_id")
    ans_text = request.POST.get("answer_text", "").strip()
    # Scoped to the requesting user's own session: without this, any
    # authenticated user could submit an answer against any ResumeQuestion id
    # (e.g. a sequential guess), overwriting another candidate's answer and
    # score on a question that was never asked to them.
    question = get_object_or_404(ResumeQuestion, id=q_id, session__resume__user=request.user)
    if not question.session.camera_verified_at:
        return JsonResponse({
            "error": "camera_required",
            "message": "Camera access is required to attend the interview. Please allow camera access and try again.",
        }, status=403)
    if question.session.malpractice_status == ResumeInterviewSession.MALPRACTICE_TERMINATED:
        return JsonResponse({
            "error": "malpractice_terminated",
            "message": "This interview was ended due to repeated malpractice violations.",
        }, status=403)

    # The browser re-sends an answer if the response was lost on the network.
    # An answer that was already scored is returned as stored — never scored
    # twice, and never rejected as late because the retry arrived after the timer.
    existing = ResumeAnswer.objects.filter(question=question).first()
    if existing and existing.text:
        return JsonResponse({"score": existing.score or 0, "feedback": existing.feedback or "",
                             "timed_out": existing.timed_out, "display_text": existing.text})

    elapsed = (timezone.now() - question.presented_at).total_seconds() if question.presented_at else 0
    hard_limit = ANSWER_TIME_LIMIT_SECONDS + ANSWER_TIME_GRACE_SECONDS
    timed_out = elapsed > ANSWER_TIME_LIMIT_SECONDS

    spoken = request.POST.get("spoken") == "1"
    if elapsed > hard_limit:
        # Arrived long after the 30s window (well past the auto-submit's own
        # network round trip) — discard whatever was sent rather than reward
        # extra thinking time past the limit.
        ans_text = ""
    elif spoken:
        # The recording travels with the answer and is transcribed only AFTER
        # the deadline check above, so transcription time can never make an
        # answer count as late. The browser's live captions are the fallback.
        ans_text = _transcribe_interview_audio(request.FILES.get("audio")) or ans_text

    if elapsed > hard_limit:
        raw_score = 0
        feedback = "No answer was submitted within the time limit."
    elif not ans_text:
        raw_score = 0
        feedback = "No answer was submitted."
    else:
        # Cross-check the answer against the candidate's actual resume: an answer
        # claiming skills/experience the resume does not support must not score
        # full marks (see RESUME CONSISTENCY CHECK in evaluate_answer).
        eval_res = evaluate_answer(question.question_text, ans_text, topic=question.topic,
                                   resume_context=_safe_resume_context(question.session),
                                   spoken=spoken)
        raw_score = eval_res.get("score", 0)
        # Each question carries 5 marks
        try:
            raw_score = max(0, min(5, int(raw_score)))
        except (ValueError, TypeError):
            raw_score = 0
        feedback = eval_res.get("feedback", "")
        # For spoken answers the same call also recovers what the candidate
        # meant (accent, slang, broken grammar, misheard words); that version
        # is what was scored, so it is what gets stored and shown.
        ans_text = eval_res.get("interpreted") or ans_text

    ResumeAnswer.objects.update_or_create(question=question, defaults={"text": ans_text, "score": raw_score, "feedback": feedback, "timed_out": timed_out})

    # Save to global ScoreRecord — once per question (a server-side timeout may
    # already have recorded this question before a late answer replaced it).
    if not existing:
        ScoreRecord.objects.create(
            user=request.user,
            module="interview",
            score=raw_score,
            max_score=5,
            label=question.topic
        )

    return JsonResponse({"score": raw_score, "feedback": feedback, "timed_out": timed_out,
                         "display_text": ans_text})


def _resume_context(session):
    """The resume profile answers are cross-checked against (skills, years,
    candidate type, domain). Built once per interview and cached — it does not
    change between answers, and rebuilding it added ~50-100ms to every one."""
    from django.core.cache import cache
    from career_app.resume_utils import (
        extract_resume_skills, classify_candidate_type, extract_experience_years,
        detect_resume_industries,
    )
    key = f"rb_resume_context_{session.id}"
    ctx = cache.get(key)
    if ctx is None:
        rtext = session.resume.extracted_text or ""
        skills = extract_resume_skills(rtext, session.matching_skills)
        years = extract_experience_years(rtext)
        ctx = {
            "skills": skills,
            "years": years,
            "candidate_type": classify_candidate_type(rtext, skills, years=years),
            "domain": detect_resume_industries(rtext, skills),
        }
        cache.set(key, ctx, 3 * 60 * 60)
    return ctx


def _safe_resume_context(session):
    """_resume_context, but scoring goes ahead without the profile rather than
    fail if the resume can't be read."""
    try:
        return _resume_context(session)
    except Exception:
        logger.exception("Resume context unavailable; scoring without it.")
        return None


_AUDIO_EXTENSIONS = {
    "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4",
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/mpeg": "mp3",
}


def _transcribe_interview_audio(audio_file):
    """Sarvam (Indian-English) transcript of an answer recording, or '' if there
    is no recording or the speech service fails — the caller then falls back to
    the browser's live captions, so a failed transcription never loses an answer."""
    api_key = getattr(settings, "SARVAM_API_KEY", "")
    if not audio_file or not api_key:
        return ""
    raw_ct = (audio_file.content_type or "audio/webm").split(";")[0].strip()
    ext = _AUDIO_EXTENSIONS.get(raw_ct, "webm")
    audio_bytes = audio_file.read()
    if not audio_bytes:
        return ""
    for data_opts in ({"model": "saarika:v2.5", "language_code": "en-IN"}, {}):
        try:
            response = requests.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": api_key},
                data=data_opts,
                files={"file": (f"recording.{ext}", audio_bytes, raw_ct)},
                timeout=20,
            )
            response.raise_for_status()
            return (response.json().get("transcript") or "").strip()
        except (requests.exceptions.RequestException, ValueError) as e:
            body = (getattr(getattr(e, "response", None), "text", "") or "")[:500]
            logger.warning(f"Sarvam STT failed (opts={data_opts}): {e} | body={body}")
    return ""


@login_required
@require_POST
def resume_transcribe_answer(request):
    """
    Accepts an audio recording from the interview page, transcribes it using
    Sarvam AI STT (/speech-to-text), and returns the transcribed text.
    """
    audio_file = request.FILES.get("audio")
    if not audio_file:
        logger.warning("resume_transcribe_answer called without audio file.")
        return JsonResponse({"success": False, "error": "No audio file provided."}, status=400)

    api_key = getattr(settings, "SARVAM_API_KEY", "")
    if not api_key:
        logger.error("SARVAM_API_KEY is not configured.")
        return JsonResponse({"success": False, "error": "STT service is not configured."}, status=500)

    SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

    try:
        # Log audio metadata for debugging
        file_size = getattr(audio_file, 'size', 0)
        if file_size == 0:
            # Fallback: read to check size
            audio_file.seek(0, 2)  # seek to end
            file_size = audio_file.tell()
            audio_file.seek(0)
        logger.info(f"STT audio: name={audio_file.name}, type={audio_file.content_type}, size={file_size} bytes")

        if file_size == 0:
            return JsonResponse({"success": False, "error": "Recording too short, please try again."}, status=400)

        # Clean content-type (strip codec params like ';codecs=opus')
        raw_ct = (audio_file.content_type or "audio/webm").split(";")[0].strip()
        ext = {
            "audio/webm": "webm",
            "audio/ogg": "ogg",
            "audio/mp4": "mp4",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
            "audio/mpeg": "mp3",
        }.get(raw_ct, "webm")

        audio_file.seek(0)
        audio_bytes = audio_file.read()
        # For best accuracy use the latest `saarika` model pinned to Indian English.
        # (The /speech-to-text endpoint uses the `saarika` family - NOT `saaras`,
        # which is the translate endpoint - and does not accept a `mode` param.)
        # If the model/lang combo is rejected, fall back to Sarvam's default model.
        response = None
        last_status = None
        last_body = ""
        for data_opts in ({"model": "saarika:v2.5", "language_code": "en-IN"}, {}):
            try:
                response = requests.post(
                    SARVAM_STT_URL,
                    headers={"api-subscription-key": api_key},
                    data=data_opts,
                    files={"file": (f"recording.{ext}", audio_bytes, raw_ct)},
                    timeout=45,
                )
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                err_response = getattr(e, "response", None)
                last_status = getattr(err_response, "status_code", None)
                # Sarvam puts the precise reason (e.g. rate limit, product not
                # enabled, quota) in the body — capture it, not just the status.
                last_body = (getattr(err_response, "text", "") or "")[:1024]
                logger.warning(
                    f"Sarvam STT attempt failed (opts={data_opts}, status={last_status}): {e} | body={last_body}"
                )
                response = None
                continue
        if response is None:
            # STT (the Saarika speech-to-text product) is billed and gated
            # SEPARATELY from the sarvam chat model — a healthy chat balance does
            # not imply STT access. A 401/403 here means Sarvam rejected the STT
            # request itself: the key lacks STT/Saarika access, STT is not enabled
            # on the plan, or a per-minute rate limit was hit. The body says which.
            if last_status in (401, 403):
                logger.error(
                    "Sarvam STT rejected (HTTP %s): the key/plan may lack Speech-to-Text (Saarika) "
                    "access or hit a rate limit — this is independent of the chat-model credits. "
                    "Sarvam response: %s",
                    last_status, last_body or "(no body)",
                )
                return JsonResponse(
                    {"success": False, "error": "Speech service is temporarily unavailable."},
                    status=503,
                )
            # A 400 on a large file is usually audio that exceeds Sarvam's
            # sync-STT length limit; a shorter recording will succeed.
            if last_status == 400:
                if file_size > 500_000:
                    logger.warning("Sarvam STT rejected a large recording (%d bytes) with HTTP 400.", file_size)
                    return JsonResponse(
                        {"success": False, "error": "That recording was too long to transcribe. Please answer in a shorter take."},
                        status=400,
                    )
                else:
                    logger.warning("Sarvam STT rejected a short/empty recording (%d bytes) with HTTP 400.", file_size)
                    return JsonResponse(
                        {"success": False, "error": "Recording too short, please try again."},
                        status=400,
                    )
            raise requests.exceptions.RequestException("All Sarvam STT attempts failed")
        data = response.json()
        transcript = data.get("transcript", "")

        if not transcript or not transcript.strip():
            return JsonResponse({"success": False, "error": "Could not hear anything. Please try again."}, status=400)

        word_count = len(transcript.strip().split())
        if word_count < 15:
            return JsonResponse({"success": False, "error": "Your answer is too short. Please provide an answer of at least 15 words."}, status=400)

        logger.info(f"Interview voice answer transcribed ({len(transcript)} chars)")
        return JsonResponse({"success": True, "text": transcript.strip()})
    except requests.exceptions.RequestException as e:
        logger.error(f"Sarvam STT request failed: {e}")
        # Capture response body for debugging
        if e.response is not None:
            try:
                logger.error(f"Sarvam STT response status: {e.response.status_code}, body: {e.response.text[:2048]}")
            except Exception:
                pass
        return JsonResponse({"success": False, "error": "Speech service is temporarily unavailable."}, status=500)
    except Exception:
        logger.exception("resume_transcribe_answer exception")
        return JsonResponse({"success": False, "error": "Something went wrong on our end. Please try again."}, status=500)


@login_required
def resume_analytics(request):
    # BUG-05 fix: re-check the plan at render time so expired/downgraded users
    # cannot view interview results and job recommendations.
    if not _can_access_interview(request.user):
        return redirect('pro_page')

    s_id = request.session.get("rb_interview_session_id")
    try:
        session = (
            ResumeInterviewSession.objects.get(id=s_id)
            if s_id
            else ResumeInterviewSession.objects.filter(
                resume__user=request.user
            ).order_by("-start_time").first()
        )
    except ResumeInterviewSession.DoesNotExist:
        session = None

    if not session: return redirect("resume_builder")
    
    questions = session.questions.all().order_by("order")
    total_questions = questions.count()
    
    results = []
    total_raw_score = 0
    answered_count = 0
    
    for q in questions:
        try:
            ans = q.answer
            score = ans.score if ans.score is not None else 0
            results.append({
                "topic": q.topic,
                "difficulty": q.difficulty,
                "question": q.question_text,
                "answer": ans.text,
                "score": score,
                "feedback": ans.feedback or ""
            })
            total_raw_score += score
            answered_count += 1
        except ResumeAnswer.DoesNotExist:
            results.append({
                "topic": q.topic,
                "difficulty": q.difficulty,
                "question": q.question_text,
                "answer": "",
                "score": 0,
                "feedback": "No answer provided."
            })
            
    # Calculate scaled integer total score out of 100 (each question = 5 marks)
    max_possible_raw = (total_questions * 5) if total_questions > 0 else 100
    scaled_percentage = (total_raw_score / max_possible_raw * 100) if max_possible_raw > 0 else 0
    total_integer_score = math.ceil(scaled_percentage)
    avg_score = (total_raw_score / total_questions) if total_questions > 0 else 0
    if total_integer_score > 100:
        total_integer_score = 100

    is_passed = (total_integer_score >= PASSING_SCORE)
    session.total_score = total_integer_score
    session.is_passed = is_passed
    session.is_completed = True
    session.save()

    import json
    json_data = json.dumps(results)

    # Experience-filtered jobs if passed
    years_exp = extract_experience_years(session.resume.extracted_text)
    matching_skills = session.matching_skills or []
    suitable_jobs = []
    
    if is_passed:
        suitable_jobs = _get_matched_jobs(
            matching_skills,
            years_experience=years_exp,
            max_results=_job_recommendation_limit(request.user),
        )
        for job in suitable_jobs:
            job.salary_display = job.get_salary_display_for_user(request.user)

    context = {
        "session": session,
        "data": results,
        "total_integer_score": total_integer_score,
        "avg_score": avg_score,
        "is_passed": is_passed,
        "years_exp": years_exp,
        "suitable_jobs": suitable_jobs,
        "total_questions": total_questions,
        "answered_count": answered_count,
        "json_data": json_data,
        "passing_score": PASSING_SCORE,
        # Below the pass mark: send the (paid) user to the Skill Up content of
        # the role they picked on the career-path page.
        "skillup_url": None if is_passed else _skillup_url_for(request),
        "target_role": request.session.get("rb_role"),
        "error": None
    }
    return render(request, "resume_analytics.html", context)


# ── BUG-03 fix: Razorpay webhook ─────────────────────────────────────────────
# Activates the plan server-side so it succeeds even when the browser closes
# before the frontend callback fires.  Register this URL in your Razorpay
# Dashboard → Webhooks as:  https://<your-domain>/pro/webhook/razorpay/
# Events to subscribe: payment.captured
# Secret: set RAZORPAY_WEBHOOK_SECRET in your .env

@csrf_exempt
def razorpay_webhook(request):
    """
    BUG-03 fix: Server-side webhook that activates the plan after a successful
    payment capture.  This fires independently of the browser, so the plan is
    granted even when the user closes the tab before the frontend callback runs.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    if not webhook_secret:
        logger.error('RAZORPAY_WEBHOOK_SECRET is not configured — webhook rejected.')
        return JsonResponse({'error': 'Webhook secret not configured.'}, status=500)

    # 1. Verify the Razorpay-Signature header.
    received_sig = request.headers.get('X-Razorpay-Signature', '')
    expected_sig = hmac.new(  # noqa: S324 — Razorpay mandates SHA-256
        webhook_secret.encode('utf-8'),
        msg=request.body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(received_sig, expected_sig):
        logger.warning('Razorpay webhook signature mismatch — ignored.')
        return JsonResponse({'error': 'Invalid signature.'}, status=400)

    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    event = payload.get('event', '')
    if event in ('refund.created', 'refund.processed'):
        return _handle_refund_event(payload)
    if event != 'payment.captured':
        # Not the event we care about — acknowledge and move on.
        return JsonResponse({'status': 'ignored'})

    payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
    payment_id = payment_entity.get('id', '')
    order_id   = payment_entity.get('order_id', '')

    # Everything that decides entitlement is read from the ORDER. Our server
    # creates orders with the API secret, so their notes cannot be forged.
    #
    # The payment entity's notes are NOT trustworthy: they are whatever the
    # browser handed to Razorpay Checkout, so a user can pay ₹588.82 against a
    # genuine Normal order while attaching plan='pro' to the payment. They are
    # used only as a last-resort hint when the payment carries no order at all,
    # and never as a source for the amount.
    #
    # (Razorpay serialises empty notes as [] rather than {}, so anything that is
    # not a dict counts as "no notes" — .get() on a list would 500 and make
    # Razorpay retry the event for the next 24h.)
    payment_notes = payment_entity.get('notes')
    if not isinstance(payment_notes, dict):
        payment_notes = {}

    order_notes = {}
    if order_id:
        try:
            order_notes = (_razorpay_client().order.fetch(order_id) or {}).get('notes')
        except Exception as e:
            # Transient API failure — 502 so Razorpay retries the event later.
            logger.error(f'Razorpay webhook: could not fetch order {order_id}: {e}')
            return JsonResponse({'error': 'Could not resolve order.'}, status=502)
        if not isinstance(order_notes, dict):
            order_notes = {}

    order_plan = (order_notes.get('plan') or '').lower().strip()
    if order_notes.get('user_id') and order_plan in PLAN_PRICING:
        user_id = order_notes.get('user_id')
        plan = order_plan
        expected_amount = _quoted_amount_paise(order_notes, plan)
    else:
        user_id = payment_notes.get('user_id')
        plan = (payment_notes.get('plan') or '').lower().strip()
        # Price from the server's own table — never from a client-supplied note.
        expected_amount = _plan_amount_paise(plan) if plan in PLAN_PRICING else None

    if not payment_id or not user_id or plan not in PLAN_PRICING:
        logger.warning(f'Razorpay webhook: missing fields — payment_id={payment_id}, user_id={user_id}, plan={plan}')
        return JsonResponse({'error': 'Missing required fields.'}, status=400)

    # Amounts below are in INR minor units; another currency would compare a
    # different unit against the same number.
    if (payment_entity.get('currency') or 'INR') != 'INR':
        logger.warning(f'Razorpay webhook: payment {payment_id} is not in INR: {payment_entity.get("currency")!r}')
        return JsonResponse({'error': 'Unsupported currency.'}, status=400)

    # PAY-04: confirm the captured amount matches the price the order was quoted
    # at, so a low-value capture can never unlock a higher tier.
    paid_amount = payment_entity.get('amount')
    if paid_amount != expected_amount:
        logger.warning(f'Razorpay webhook amount mismatch for {payment_id}: paid={paid_amount} expected={expected_amount}')
        return JsonResponse({'error': 'Amount mismatch.'}, status=400)

    # 2. Idempotency: skip if this payment was already processed.
    if RazorpayPayment.objects.filter(razorpay_payment_id=payment_id).exists():
        logger.info(f'Razorpay webhook: payment {payment_id} already processed — skipping.')
        return JsonResponse({'status': 'already_processed'})

    # 3. Activate the plan.
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f'Razorpay webhook: user {user_id} not found.')
        return JsonResponse({'error': 'User not found.'}, status=404)

    # Resolve the plan first (this also auto-lapses an expired one), then read the
    # profile back so we never write stale field values over that update.
    current_plan = _get_user_plan(user)
    profile, _ = UserProfile.objects.get_or_create(user=user)

    # Razorpay retries a webhook for up to 24h and can deliver it late or out of
    # order, so a capture for an older, cheaper order can arrive after the user
    # has already upgraded. Record the payment either way — it must never be
    # replayable — but never let a stale event pull an active subscription down a
    # tier or restart its 1-year clock.
    is_downgrade = profile.is_subscription_active() and _is_plan_downgrade(current_plan, plan)

    # One transaction, for the same reason as the verify path: a payment recorded
    # without the activation beside it is a payment that can never be retried.
    with transaction.atomic():  # type: ignore[attr-defined]
        payment, created = RazorpayPayment.objects.get_or_create(
            razorpay_payment_id=payment_id,
            defaults={
                'user': user,
                'razorpay_order_id': order_id,
                'plan_type': plan,
                'amount_paise': paid_amount,
                'status': (RazorpayPayment.STATUS_REFUND_REQUIRED if is_downgrade
                           else RazorpayPayment.STATUS_CAPTURED),
            },
        )
        # PAY-P01: the row already existing means the browser callback committed
        # it between the exists() check above and this line — the two fire within
        # milliseconds of the same capture, so that window is hit routinely. The
        # callback has already activated this payment; activating again would
        # stack a second year onto one payment, because renewing an active plan
        # extends the remaining term.
        if created and not is_downgrade:
            payment.assign_invoice_number()
            _activate_plan(profile, plan)

    if not created:
        logger.info(f'Razorpay webhook: payment {payment_id} already activated by the callback — skipping.')
        return JsonResponse({'status': 'already_processed'})

    if is_downgrade:
        # Reaching here means the browser callback never applied this payment
        # either (that path records it, and a recorded payment short-circuits
        # above as already_processed) — so this is a real capture that bought
        # the user nothing.
        logger.warning(
            f'REFUND REQUIRED: webhook captured payment {payment_id} for {plan}, user {user_id} '
            f'is already on the higher {current_plan} plan — not applied.'
        )
        return JsonResponse({'status': 'ignored_downgrade'})

    invoice_url = request.build_absolute_uri(reverse('payment_invoice', args=[payment.pk]))
    _send_payment_receipt(
        user, plan, payment_id, paid_amount, profile.subscription_expiry(),
        invoice_number=payment.invoice_number, invoice_url=invoice_url,
    )

    logger.info(f'Razorpay webhook: activated {plan} plan for user {user_id} via payment {payment_id}.')
    return JsonResponse({'status': 'ok'})
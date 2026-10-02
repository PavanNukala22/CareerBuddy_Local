import os
import re
import csv
import logging
import pypdf
from functools import reduce
from operator import or_
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from .models import EmployerProfile, JobPosting, JobApplication
from .forms import EmployerProfileForm, JobPostingForm, JobApplicationForm, ApplicationStatusForm
from core.email_utils import send_transactional_email, sanitize_header_value

logger = logging.getLogger(__name__)


def notify_employer_new_application(request, app):
    """Email the employer that a new application arrived for one of their jobs.

    Fills the §24.4 gap where a new application was only visible by manually
    checking the dashboard. Seeded/system jobs have no employer, and an employer
    may not have supplied a contact address, so both cases are skipped quietly —
    a candidate's application must never fail because the employer is unreachable.
    """
    job = app.job
    try:
        employer = job.employer
    except EmployerProfile.DoesNotExist:
        employer = None
    if not employer:
        return
    to_email = (employer.hr_mail or getattr(employer.user, 'email', '') or '').strip()
    if not to_email:
        logger.info(f'Employer for job {job.id} has no contact email — new-application alert not sent.')
        return
    try:
        dashboard_url = request.build_absolute_uri(
            reverse('employer_portal:application_detail', args=[app.pk])
        )
    except Exception:
        dashboard_url = request.build_absolute_uri('/employer/applications/')
    send_transactional_email(
        subject=f'New application for {job.title}',
        to_email=to_email,
        template_name='emails/new_application_employer.html',
        context={
            'company_name': employer.company_name,
            'job_title': job.title,
            'applicant_name': app.applicant_name,
            'applicant_email': app.applicant_email,
            'applicant_phone': app.applicant_phone,
            'applicant_skills': app.applicant_skills,
            'years_experience': app.years_experience,
            'dashboard_url': dashboard_url,
        },
    )


# Human-friendly line shown to the candidate for each application status.
STATUS_UPDATE_MESSAGES = {
    'applied': 'Your application has been received and is in the queue for review.',
    'reviewing': 'Good news — the employer is now reviewing your application.',
    'shortlisted': 'Congratulations! You have been shortlisted for this role.',
    'interview': 'You have been selected for an interview. The employer will share the details with you shortly.',
    'offered': 'Congratulations! The employer has extended an offer for this role.',
    'rejected': 'Thank you for your interest. The employer has decided not to move forward with your application this time. Keep going — the right opportunity is out there.',
}


def notify_candidate_status_change(request, app):
    """Email the candidate that an employer changed their application status.

    Fills the §24.4 gap where the six-state pipeline was invisible to the
    applicant. Called only when the status actually changed.
    """
    # Idempotent per application: the same status processed again (a
    # resubmitted form, a retried request) must not produce a second email,
    # but a different application by the same candidate — another job at the
    # same company — has its own marker and is notified on its own.
    if app.status == app.last_notified_status:
        return False

    # Deliver to the candidate's registered account email, and also to the
    # address typed on this application when it differs (a candidate may
    # apply under a different email than the one they log in with).
    recipients = []
    for candidate_email in (
        getattr(app.applicant_user, 'email', '') if app.applicant_user_id else '',
        app.applicant_email,
    ):
        candidate_email = (candidate_email or '').strip()
        if candidate_email and candidate_email.lower() not in {r.lower() for r in recipients}:
            recipients.append(candidate_email)
    if not recipients:
        return False
    job = app.job
    sent_any = False
    for to_email in recipients:
        sent_any = send_transactional_email(
            subject=f'Update on your application for {job.title}',
            to_email=to_email,
            template_name='emails/application_status_update.html',
            context={
                'applicant_name': app.applicant_name,
                'job_title': job.title,
                'company_name': (job.employer.company_name if job.employer else 'Career Buddy Partner'),
                'status_label': app.get_status_display(),
                'status_message': STATUS_UPDATE_MESSAGES.get(
                    app.status, 'The status of your application has been updated.'
                ),
                # Deep-link to this specific application. The view is login-gated
                # and ownership-scoped, so a logged-out candidate is bounced to
                # login and returned here, and nobody else can open it by id.
                'dashboard_url': request.build_absolute_uri(
                    reverse('my_application_detail', args=[app.pk])
                ),
            },
        ) or sent_any
    if sent_any:
        app.last_notified_status = app.status
        app.save(update_fields=['last_notified_status'])
    return sent_any


def student_applications_for(user):
    """Applications that belong to this student.

    An application is the student's if it was linked to their account at
    apply time, or — for applications submitted through the public form
    before/without logging in — if it carries their registered email. This is
    the same identity rule candidate search already uses to attribute
    applications to a registered candidate.
    """
    email = (getattr(user, 'email', '') or '').strip()
    owner = Q(applicant_user=user)
    if email:
        owner |= Q(applicant_email__iexact=email)
    return JobApplication.objects.filter(owner).select_related('job', 'job__employer')


@login_required
def my_application_detail(request, pk):
    """Student-facing view of one of their own applications (linked from the
    status-update email). Foreign ids 404 rather than 403 so the existence
    of other candidates' applications is not disclosed."""
    app = get_object_or_404(student_applications_for(request.user), pk=pk)
    return render(request, 'jobs/my_application.html', {'app': app})


def parse_experience_range(exp_query):
    """Parse an experience-filter value like "3-5", "5+" or "fresher" into
    (min_years, max_years) — max_years is None for an open-ended range
    ("5+"). (None, None) means no filter at all.

    Both candidate-search paths (search_registered_candidates and
    parse_resumes_from_folder below) previously only pulled the FIRST digit
    out of the query with a bare regex, e.g. "3-5" became a single value 3,
    then filtered as "years >= 3" — so selecting "3-5 Years" actually
    returned every candidate with 3+ years, including 10, 20 years, since
    the "-5" upper bound was silently discarded. This applies the full
    range on both ends instead.
    """
    if not exp_query:
        return None, None
    q = exp_query.strip().lower()
    if q in ('fresher', '0'):
        return 0, 0
    m = re.match(r'^(\d+)\s*-\s*(\d+)$', q)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r'^(\d+)\s*\+$', q)
    if m:
        return int(m.group(1)), None
    # Fallback for a bare number (no range/plus syntax) — treat as "at
    # least N", matching the old single-sided behaviour for any caller not
    # using the dropdown's "N-M" / "N+" / "fresher" values.
    m = re.search(r'(\d+)', q)
    if m:
        return int(m.group(1)), None
    return None, None

def skill_term_hits(term, text):
    if not term or not text:
        return 0
    term_lower = term.lower()
    text_lower = text.lower()
    pattern = r'(?<![a-z0-9+#.])' + re.escape(term_lower) + r'(?![a-z0-9+#.])'
    return len(re.findall(pattern, text_lower))


def parse_resumes_from_folder(skill_query, location_query=None, exp_query=None):
    results = []
    resumes_dir = os.path.join(str(settings.MEDIA_ROOT), 'resumes')
    
    if not os.path.exists(resumes_dir):
        return results

    skill_terms = [s.strip().lower() for s in skill_query.split(',') if s.strip()]
    loc_term = location_query.strip().lower() if location_query else None

    # Regex patterns
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    phone_pattern = re.compile(r'\(?\+?[0-9]*\)?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}')
    
    exp_min, exp_max = parse_experience_range(exp_query)

    all_matched_candidates = []

    for filename in os.listdir(resumes_dir):
        if not filename.lower().endswith('.pdf'):
            continue
            
        file_path = os.path.join(resumes_dir, filename)
        try:
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
                
            text_lower = text.lower()
            
            # Location Filter (Strict Exact Match - restricted to top of page for residence)
            if loc_term:
                header_text = text_lower[:500] # Check first 500 chars for residence
                if not re.search(rf'\b{re.escape(loc_term)}\b', header_text):
                    continue

            # Experience Filter — matches the selected range (e.g. "3-5 Years"
            # only keeps resumes with 3 <= years <= 5), not just a lower bound.
            exp_found_text = "Not Available"
            exp_found_years = None
            # Look for patterns like "3+ years", "3 years", "3 yrs"
            exp_results = re.search(r'(\d+)\+?\s*(?:year|yr)', text_lower)
            if exp_results:
                exp_found_years = int(exp_results.group(1))
                exp_found_text = f"{exp_found_years}+ Years"

            if exp_min is not None or exp_max is not None:
                if exp_found_years is None:
                    continue
                if exp_min is not None and exp_found_years < exp_min:
                    continue
                if exp_max is not None and exp_found_years > exp_max:
                    continue

            # Match skills anywhere in the document
            matched_skills = []
            for term in skill_terms:
                if re.search(rf'\b{re.escape(term)}\b', text_lower) or term in text_lower:
                    matched_skills.append(term)

            # If skill search is specified, we must match at least one skill
            if skill_terms and not matched_skills:
                continue

            # Relevance score: total number of times the searched skill term(s)
            # appear anywhere in the resume. A resume that mentions "python" more
            # often is treated as a stronger match and ranked higher.
            skill_count = 0
            for term in skill_terms:
                skill_count += len(re.findall(rf'\b{re.escape(term)}\b', text_lower))
            
            # Extract details
            email_match = email_pattern.search(text)
            email = email_match.group(0) if email_match else "Not Available"
            
            phone_match = phone_pattern.search(text)
            phone = phone_match.group(0) if phone_match else "Not Available"
            
            # Simple heuristic for location extraction (usually near phone)
            location_extracted = "Not Available"
            if phone_match:
                # Look for a string after the phone number, often separated by | or ■
                after_phone = text.split(phone_match.group(0))[-1].split('\n')[0]
                loc_match = re.search(r'[|■]\s*([^|■\n]+)', after_phone)
                if loc_match:
                    location_extracted = loc_match.group(1).strip()
                elif ',' in after_phone:
                    location_extracted = after_phone.strip(' |■\t')

            lines = [line.strip() for line in text.split('\n') if line.strip()]
            name = lines[0] if lines else "Not Available"
            
            if len(name.split()) > 4 or 'resume' in name.lower() or 'curriculum' in name.lower():
                clean_name = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')
                clean_name = re.sub(r'(?i)\bresume\b|\bcv\b\b|\d', '', clean_name).strip()
                name = clean_name if clean_name else name

            all_matched_candidates.append({
                'name': name,
                'email': email,
                'phone': phone,
                'location': location_extracted,
                'experience': exp_found_text,
                'exp_years': exp_found_years or 0,
                'skills': matched_skills if skill_terms else [],
                'skill_count': skill_count,
                'resume_url': f"/media/resumes/{filename}"
            })
        except Exception:
            logger.exception("Error parsing resume file %s during folder scan", filename)
            continue



    # Rank by relevance: resumes with the most occurrences of the searched
    # skill appear first (e.g. searching "python" surfaces the resume that
    # mentions python the most times at the top).
    if skill_terms:
        all_matched_candidates.sort(key=lambda c: c['skill_count'], reverse=True)

    # Deduplicate candidates. The resume builder saves a new file on every
    # upload, so the same person can have many near-identical copies on disk.
    # Collapse them to a single card keyed by email (falling back to name +
    # phone). Because the list is already sorted by relevance, the first copy
    # we keep is the strongest match for that candidate.
    deduped = []
    seen = set()
    for c in all_matched_candidates:
        email = (c.get('email') or '').strip().lower()
        name = (c.get('name') or '').strip().lower()
        phone = re.sub(r'\D', '', c.get('phone') or '')
        if email and email != 'not available':
            key = ('email', email)
        elif phone:
            key = ('phone', phone)
        else:
            key = ('name', name)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)

    return deduped

def home(request):
    """Recruiter Portal Landing Page (Hero Section)"""
    # Exclude seeded jobs from public counts; they are only used by CareerBuddy matching
    total_jobs = JobPosting.objects.filter(status='active', is_seeded=False).count()
    total_companies = EmployerProfile.objects.filter(user__is_active=True).exclude(user__username__startswith='seed_').count()
    
    return render(request, 'jobs/employer_home.html', {
        'total_jobs': total_jobs,
        'total_companies': total_companies,
    })

@login_required(login_url='employer_portal:employer_login')
def download_candidates_csv(request):
    if request.session.get('portal') != 'employer':
        from django.contrib.auth import logout as auth_logout
        auth_logout(request)
        return redirect('job_home')

    search = request.GET.get('q', '').strip()
    experience = request.GET.get('experience', '').strip()
    location = request.GET.get('location', '').strip()
    is_view = request.GET.get('view', 'false') == 'true'
    
    query = search if search else ""
    results = []
    if query:
        results = search_registered_candidates(query, location, experience)

    content_type = 'text/plain' if is_view else 'text/csv'
    response = HttpResponse(content_type=content_type)

    if not is_view:
        response['Content-Disposition'] = 'attachment; filename="candidates.csv"'

    writer = csv.writer(response)
    writer.writerow(['Name', 'Email', 'Phone Number', 'Skills', 'Experience', 'Location', 'Resume Link'])

    for p in results:
        resume_full_url = ''
        if p.get('resume_url'):
            base_url = f"{request.scheme}://{request.get_host()}"
            resume_full_url = f"{base_url}{p['resume_url']}"
        writer.writerow([
            p['name'], p['email'], p['phone'], ', '.join(p['skills']),
            p['experience'], p.get('location', ''), resume_full_url,
        ])

    return response

def job_list(request):
    # Exclude seeded/system jobs from the public job board
    jobs = JobPosting.objects.filter(status='active', is_seeded=False).select_related('employer')
    search = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    job_type = request.GET.get('job_type', '').strip()
    experience = request.GET.get('experience', '').strip()
    skills = request.GET.get('skills', '').strip() or search # fallback to search if skills not provided

    if search:
        search_query = reduce(or_, [
            Q(title__icontains=search),
            Q(skills_required__icontains=search),
            Q(employer__company_name__icontains=search)
        ])
        jobs = jobs.filter(search_query)
    if location:
        jobs = jobs.filter(location__icontains=location)
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    if experience:
        jobs = jobs.filter(experience=experience)

    # Candidate search (from registered students in the DB)
    results = None
    if skills:
        results = search_registered_candidates(skills)

    
    return render(request, 'jobs/job_list.html', {
        'jobs': jobs, 'search': search, 'location': location,
        'job_type': job_type, 'experience': experience,
        'job_types': JobPosting.JOB_TYPE_CHOICES,
        'exp_choices': JobPosting.EXPERIENCE_CHOICES,
        'results': results, 'query': skills,
    })

def job_detail(request, pk):
    job = get_object_or_404(JobPosting, pk=pk, status='active')
    applied = False
    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.job = job
            if request.user.is_authenticated:
                app.applicant_user = request.user
                app.interview_session = _qualifying_interview_session(request)
            try:
                app.save()

                # Send Thank You Email
                send_transactional_email(
                    subject=f'Application Received: {job.title}',
                    to_email=app.applicant_email,
                    template_name='emails/thank_you_application.html',
                    context={
                        'applicant_name': app.applicant_name,
                        'job_title': job.title,
                        'company_name': job.employer.company_name if job.employer else "CareerBuddy Partner",
                        'dashboard_url': request.build_absolute_uri(reverse('student_dashboard')),
                    },
                )

                # Notify the employer that a new application arrived (§24.4 gap).
                notify_employer_new_application(request, app)

                messages.success(request, 'Application submitted successfully! A confirmation email has been sent.')
                # Namespaced: the URL conf only registers this view under
                # employer_portal/urls.py (app_name='employer_portal').
                # jobs_app/urls.py declares an unnamespaced 'job_detail' too,
                # but that urlconf is never included anywhere, so a bare
                # redirect('job_detail', ...) always raised NoReverseMatch —
                # silently, since it happened inside this function's own
                # broad except below, masking every successful application
                # as "You have already applied for this job."
                return redirect('employer_portal:job_detail', pk=pk)
            except Exception:
                # Was a bare `except Exception` with no logging, so a genuine
                # error (DB constraint, template, mail) was indistinguishable
                # from an actual duplicate and left no trace to diagnose it by.
                logger.exception(f'job_detail: application save failed for job {pk}')
                messages.error(request, 'You have already applied for this job.')
    else:
        form = JobApplicationForm()
    job.salary_display = job.get_salary_display_for_user(request.user)
    return render(request, 'jobs/job_detail.html', {'job': job, 'form': form, 'applied': applied})


# --- EMPLOYER VIEWS ----------------------------------------------------------

def _employer_profile_complete(profile):
    """A profile counts as complete once GSTIN and PAN are on file.

    EmployerRegisterForm creates an EmployerProfile row immediately at sign-up
    (company name, industry, HR contact) but leaves company_gst/company_pan_tin
    optional there — the same two fields EmployerProfileForm (used by the
    create/edit views below) requires. So "has a company profile" for the
    purpose of the FSD's "employer without a profile is redirected to create
    one" behaviour means "has completed it with GST/PAN", not merely "has a
    row" — every self-registered employer already has a row.
    """
    return bool(profile.company_gst and profile.company_pan_tin)


@login_required(login_url='employer_portal:employer_login')
def employer_dashboard(request):
    if request.session.get('portal') != 'employer':
        from django.contrib.auth import logout as auth_logout
        auth_logout(request)
        return redirect('job_home')

    try:
        profile = request.user.employer_profile
    except EmployerProfile.DoesNotExist:
        messages.warning(request, 'Please complete your company profile first.')
        return redirect('employer_portal:employer_profile_create')

    if not _employer_profile_complete(profile):
        messages.warning(request, 'Please complete your company profile first.')
        return redirect('employer_portal:employer_profile_create')

    own_jobs = JobPosting.objects.filter(employer=profile).annotate(app_count=Count('applications'))
    all_platform_jobs = JobPosting.objects.all()

    jobs = own_jobs if own_jobs.exists() else all_platform_jobs.annotate(app_count=Count('applications'))
    
    total_jobs_count = own_jobs.count() if own_jobs.exists() else all_platform_jobs.count()
    active_jobs_count = own_jobs.filter(status='active').count() if own_jobs.exists() else all_platform_jobs.filter(status='active').count()

    total_apps = JobApplication.objects.filter(
        Q(job__employer=profile) | Q(source='resume_parsed')
    ).distinct().count()

    recent_apps = JobApplication.objects.filter(
        Q(job__employer=profile) | Q(source='resume_parsed')
    ).select_related('job').distinct().order_by('-applied_at')[:5]

    return render(request, 'employer/dashboard.html', {
        'profile': profile,
        'jobs': jobs,
        'own_jobs': own_jobs,
        'total_jobs_count': total_jobs_count,
        'total_apps': total_apps,
        'active_jobs': active_jobs_count,
        'recent_apps': recent_apps,
    })

@login_required(login_url='employer_portal:employer_login')
def employer_profile_create(request):
    existing_profile = getattr(request.user, 'employer_profile', None)
    if existing_profile and _employer_profile_complete(existing_profile):
        return redirect('employer_portal:dashboard')
    if request.method == 'POST':
        # Update the row registration already created rather than trying to
        # insert a second one (EmployerProfile.user is one-to-one).
        form = EmployerProfileForm(request.POST, request.FILES, instance=existing_profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, 'Company profile created!')
            return redirect('employer_portal:dashboard')
    else:
        form = EmployerProfileForm(instance=existing_profile)
    return render(request, 'employer/profile_form.html', {'form': form, 'title': 'Create Company Profile'})

@login_required(login_url='employer_portal:employer_login')
def employer_profile_edit(request):
    profile = get_object_or_404(EmployerProfile, user=request.user)
    if request.method == 'POST':
        form = EmployerProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated!')
            return redirect('employer_portal:dashboard')
    else:
        form = EmployerProfileForm(instance=profile)
    # 'profile' is what templates/includes/mask_reveal_field.html reads
    # (via profile.company_pan_tin|mask_pan) to show the masked PAN — without
    # it in context the include silently fell back to its unmasked branch.
    return render(request, 'employer/profile_form.html', {'form': form, 'title': 'Edit Company Profile', 'profile': profile})

@login_required(login_url='employer_portal:employer_login')
def job_create(request):
    profile = get_object_or_404(EmployerProfile, user=request.user)
    if request.method == 'POST':
        form = JobPostingForm(request.POST, employer=profile)
        if form.is_valid():
            job = form.save(commit=False)
            job.employer = profile
            job.save()
            messages.success(request, 'Job posted successfully!')
            return redirect('employer_portal:dashboard')
    else:
        form = JobPostingForm(employer=profile)

    # Counts only this employer's own active postings — deliberately not the
    # dashboard's active_jobs figure, which falls back to a platform-wide count
    # for an employer with no jobs of their own and so would never read as 0
    # for exactly the employer this notice is meant for.
    # Shown on page open only: re-displaying it over a form the user has
    # already filled in (i.e. after a failed validation POST) would be noise.
    show_no_active_jobs_notice = (
        request.method != 'POST'
        and not JobPosting.objects.filter(employer=profile, status='active').exists()
    )

    return render(request, 'employer/job_form.html', {
        'form': form,
        'title': 'Post New Job',
        'show_no_active_jobs_notice': show_no_active_jobs_notice,
    })

@login_required(login_url='employer_portal:employer_login')
def job_edit(request, pk):
    profile = get_object_or_404(EmployerProfile, user=request.user)
    job = get_object_or_404(JobPosting.objects.filter(Q(employer=profile) | Q(is_seeded=True)), pk=pk)
    if job.employer != profile:
        job.employer = profile
        job.save()
    if request.method == 'POST':
        form = JobPostingForm(request.POST, instance=job, employer=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated!')
            return redirect('employer_portal:dashboard')
    else:
        form = JobPostingForm(instance=job, employer=profile)
    return render(request, 'employer/job_form.html', {'form': form, 'title': 'Edit Job'})

@login_required(login_url='employer_portal:employer_login')
def job_delete(request, pk):
    profile = get_object_or_404(EmployerProfile, user=request.user)
    job = get_object_or_404(JobPosting.objects.filter(Q(employer=profile) | Q(is_seeded=True)), pk=pk)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted.')
    return redirect('employer_portal:dashboard')

@login_required(login_url='employer_portal:employer_login')
def job_applications(request, pk):
    profile = get_object_or_404(EmployerProfile, user=request.user)
    job = get_object_or_404(JobPosting.objects.filter(Q(employer=profile) | Q(is_seeded=True)), pk=pk)
    applications = job.applications.all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    return render(request, 'employer/applications.html', {
        'job': job, 'applications': applications,
        'status_choices': JobApplication.STATUS_CHOICES, 'status_filter': status_filter,
    })

def _qualifying_interview_session(request):
    """The interview session the candidate is applying on the strength of —
    the one held in their browsing session — if it really is theirs."""
    s_id = request.session.get('rb_interview_session_id')
    if not s_id or not request.user.is_authenticated:
        return None
    from career_app.models import ResumeInterviewSession
    return ResumeInterviewSession.objects.filter(id=s_id, resume__user=request.user).first()


def _interview_session_for_application(app):
    """Recording to show an employer for one application.

    Prefer the interview explicitly linked to this application. Older or
    migrated applications may not have that link set, and public-form
    applications may have no applicant_user at all, so the fallback first
    narrows to the SAME resume the candidate applied with — a candidate who
    has interviewed on several resumes must not have an unrelated recording
    shown against this application — and only then widens to their newest
    passing interview rather than showing nothing.
    """
    from career_app.models import ResumeInterviewSession
    linked = app.interview_session
    if linked and linked.is_passed and linked.interview_video:
        return linked

    candidate = app.applicant_user
    if candidate is None and app.applicant_email:
        from django.contrib.auth import get_user_model
        candidate = get_user_model().objects.filter(email__iexact=app.applicant_email).first()
    if candidate is None:
        return None

    sessions = (
        ResumeInterviewSession.objects
        .filter(resume__user=candidate, is_passed=True)
        .exclude(interview_video='')
        .exclude(interview_video__isnull=True)
    )

    resume_name = (getattr(app.resume, 'name', '') or '').strip()
    if resume_name:
        sessions = sessions.filter(resume__file=resume_name)

    return sessions.order_by('-start_time').first() or (
        ResumeInterviewSession.objects
        .filter(resume__user=candidate, is_passed=True)
        .exclude(interview_video='')
        .exclude(interview_video__isnull=True)
        .order_by('-start_time')
        .first()
    )


@login_required(login_url='employer_portal:employer_login')
def application_detail(request, pk):
    profile = get_object_or_404(EmployerProfile, user=request.user)
    app = get_object_or_404(
        JobApplication.objects.filter(
            job__employer=profile
        ).select_related('job', 'job__employer'),
        pk=pk
    )
    if request.method == 'POST':
        previous_status = app.status
        form = ApplicationStatusForm(request.POST, instance=app)
        if form.is_valid():
            app = form.save()
            if app.status != previous_status:
                # Tell the candidate their status moved (§24.4 gap).
                notify_candidate_status_change(request, app)
                messages.success(request, 'Application status updated! The candidate has been notified by email.')
            else:
                messages.success(request, 'Application updated!')
            return redirect('employer_portal:application_detail', pk=pk)
    else:
        form = ApplicationStatusForm(instance=app)
    interview_session = _interview_session_for_application(app)
    return render(request, 'employer/application_detail.html', {
        'app': app, 'form': form, 'interview_session': interview_session,
    })

@login_required(login_url='employer_portal:employer_login')
def all_applications(request):
    profile = get_object_or_404(EmployerProfile, user=request.user)

    # Show applications to this employer's own jobs
    applications = JobApplication.objects.filter(
        job__employer=profile
    ).select_related('job', 'job__employer', 'applicant_user')

    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')
    source_filter = request.GET.get('source', '')

    if status_filter:
        applications = applications.filter(status=status_filter)
    if search:
        applications = applications.filter(
            Q(applicant_name__icontains=search) | Q(applicant_email__icontains=search)
        )
    if source_filter:
        applications = applications.filter(source=source_filter)

    return render(request, 'employer/all_applications.html', {
        'applications': applications,
        'status_choices': JobApplication.STATUS_CHOICES,
        'source_choices': JobApplication.SOURCE_CHOICES,
        'status_filter': status_filter,
        'source_filter': source_filter,
        'search': search,
    })

@login_required
def job_openings(request):
    """View that lists all active jobs (employer-posted + seeded) and allows applying."""
    # Show ALL active jobs - including seeded system jobs used for resume matching
    jobs = JobPosting.objects.filter(status='active').select_related('employer').order_by('is_seeded', '-created_at')

    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        job = get_object_or_404(JobPosting, id=job_id)
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            app = form.save(commit=False)
            app.job = job
            app.source = 'direct'
            app.interview_session = _qualifying_interview_session(request)
            
            # Check for duplicate application
            if app.__class__.objects.filter(job=job, applicant_email=app.applicant_email).exists():
                messages.error(request, 'You have already applied for this job with this email.')
                return redirect('employer_portal:job_openings')
                
            try:
                app.save()

                # Send Thank You Email
                company_name = sanitize_header_value(
                    job.employer.company_name if job.employer else "Career Buddy Partner"
                )
                send_transactional_email(
                    subject=f'Application Received: {job.title}',
                    to_email=app.applicant_email,
                    template_name='emails/thank_you_application.html',
                    context={
                        'applicant_name': app.applicant_name,
                        'job_title': job.title,
                        'company_name': company_name,
                        'dashboard_url': request.build_absolute_uri(reverse('student_dashboard')),
                    },
                    from_email=f"{company_name} <{settings.DEFAULT_FROM_EMAIL}>",
                )

                # Notify the employer that a new application arrived (§24.4 gap).
                notify_employer_new_application(request, app)

                messages.success(request, f'Application for {job.title} submitted successfully!')
                return redirect('employer_portal:job_openings')
            except Exception:
                messages.error(request, 'You have already applied for this job with this email.')
        else:
            error_details = " ".join([f"{field}: {', '.join(errors)}" for field, errors in form.errors.items()])
            messages.error(request, f'Failed to submit application. Errors: {error_details}')
            messages.error(request, 'Please fix the errors in the form.')
    else:
        form = JobApplicationForm()

    # "My Postings" shows only the jobs posted by this employer's account;
    # every other employer's job (and the seeded ones) belongs to All Jobs.
    own_employer_id = None
    if request.user.is_authenticated:
        own_employer_id = EmployerProfile.objects.filter(user=request.user).values_list('id', flat=True).first()
    return render(request, 'employer/job_openings.html', {
        'jobs': jobs,
        'form': form,
        'own_employer_id': own_employer_id,
    })


@login_required
def resume_apply_job(request):
    """Quick-apply endpoint called from the resume match result page.

    POST fields: job_id, applicant_name, applicant_email, applicant_phone,
                 applicant_skills, years_experience, cover_letter (optional)
    The resume file is taken from the session (rb_resume_id) if available.
    """
    if request.method != 'POST':
        return redirect('resume_job_match')

    job_id = request.POST.get('job_id')
    job = get_object_or_404(JobPosting, id=job_id, status='active')

    applicant_name  = request.POST.get('applicant_name', '').strip()
    applicant_email = request.POST.get('applicant_email', '').strip()
    applicant_phone = request.POST.get('applicant_phone', '').strip()
    applicant_skills = request.POST.get('applicant_skills', '').strip()
    years_experience = int(request.POST.get('years_experience', 0) or 0)
    cover_letter    = request.POST.get('cover_letter', '').strip()

    if not applicant_name or not applicant_email:
        messages.error(request, 'Name and email are required to apply.')
        return redirect('resume_job_match')

    # Check for duplicate application
    if JobApplication.objects.filter(job=job, applicant_email=applicant_email).exists():
        messages.warning(request, f'You have already applied for "{job.title}".')
        return redirect('resume_job_match')

    # Pull the resume file from the session-linked Resume object
    from core.models import Resume as ResumeModel
    resume_file_field = None
    resume_id = request.session.get('rb_resume_id')
    if resume_id:
        try:
            resume_obj = ResumeModel.objects.get(id=resume_id, user=request.user)
            resume_file_field = resume_obj.file
        except Exception:
            pass

    app = JobApplication(
        job=job,
        applicant_user=request.user,
        interview_session=_qualifying_interview_session(request),
        source='resume_parsed',
        applicant_name=applicant_name,
        applicant_email=applicant_email,
        applicant_phone=applicant_phone or 'N/A',
        applicant_skills=applicant_skills,
        years_experience=years_experience,
        cover_letter=cover_letter,
        status='applied',
    )
    if resume_file_field:
        app.resume = resume_file_field
    app.save()

    # Send confirmation email
    company_name = sanitize_header_value(job.employer.company_name if job.employer else 'Career Buddy Partner')
    send_transactional_email(
        subject=f'Application Received: {job.title}',
        to_email=applicant_email,
        template_name='emails/thank_you_application.html',
        context={
            'applicant_name': applicant_name,
            'job_title': job.title,
            'company_name': company_name,
            'dashboard_url': request.build_absolute_uri(reverse('student_dashboard')),
        },
        from_email=f"{company_name} <{settings.DEFAULT_FROM_EMAIL}>",
    )

    # Notify the employer that a new application arrived (§24.4 gap).
    notify_employer_new_application(request, app)

    messages.success(request, f'Successfully applied for "{job.title}"! The employer will contact you.')
    return redirect('resume_job_match')


def search_registered_candidates(skill_query='', location_query=None, exp_query=None):
    """
    Candidate search engine over REGISTERED STUDENTS and candidate resumes stored in the database
    (users.UserProfile, core.models.Resume, jobs_app.JobApplication).
    Returns candidates ranked by skill match count and experience.
    """
    from users.models import UserProfile
    try:
        from core.models import Resume as ResumeModel
    except Exception:
        ResumeModel = None
    try:
        from career_app.resume_utils import extract_experience_years
    except Exception:
        extract_experience_years = None

    raw_query = (skill_query or '').strip()
    skill_terms = []
    if raw_query:
        if ',' in raw_query:
            skill_terms = [s.strip().lower() for s in raw_query.split(',') if s.strip()]
        else:
            skill_terms.append(raw_query.lower())
            words = [w.strip().lower() for w in raw_query.split() if len(w.strip()) > 2]
            for w in words:
                if w not in skill_terms:
                    skill_terms.append(w)

    loc_term = location_query.strip().lower() if location_query else None
    exp_min, exp_max = parse_experience_range(exp_query)

    # Only genuine STUDENT-PORTAL candidates:
    #  - role='student' (registered through the student portal)
    #  - exclude employer accounts (they also get an auto-created profile)
    #  - exclude staff / superuser accounts
    profiles = (
        UserProfile.objects.filter(user__is_active=True, role='student')
        .filter(user__employer_profile__isnull=True)
        .exclude(user__is_staff=True)
        .exclude(user__is_superuser=True)
        .select_related('user')
    )

    results = []
    seen_emails = set()

    for p in profiles:
        user = p.user
        email_key = (user.email or user.username).strip().lower()

        # Skip duplicate candidates — one entry per email (registered students only)
        if email_key in seen_emails:
            continue

        # 1. Gather all resume texts for this user
        user_resumes = ResumeModel.objects.filter(user=user) if ResumeModel else []
        resume_texts = []
        if user_resumes:
            for r in user_resumes:
                if r.extracted_text:
                    resume_texts.append(r.extracted_text)
        if p.resume_text:
            resume_texts.append(p.resume_text)

        combined_resume_text = " \n ".join(resume_texts)

        # 2. Gather skills from JobApplication records (by user object or matching email)
        job_apps = JobApplication.objects.filter(
            Q(applicant_user=user) | (Q(applicant_email__iexact=user.email) & ~Q(applicant_email=''))
        )
        app_skills_list = []
        for ja in job_apps:
            if ja.applicant_skills:
                app_skills_list.append(ja.applicant_skills)

        # 3. Build comprehensive skill search blob
        skill_sources = [
            p.skills or '',
            p.abroad_skills or '',
            p.certification or '',
            " , ".join(app_skills_list),
            p.higher_education_degree or '',
            p.iti_diploma_specialization or '',
            p.bio or '',
            combined_resume_text
        ]
        skills_blob = " , ".join(s for s in skill_sources if s)
        skills_lower = skills_blob.lower()

        # Count skill matches
        skill_count = 0
        matched_terms = []
        if skill_terms:
            for term in skill_terms:
                hits = skill_term_hits(term, skills_lower)
                if hits > 0:
                    skill_count += hits
                    matched_terms.append(term)

            # If skill query provided, candidate must match at least one term
            if not matched_terms:
                continue

        # Location filter
        loc_text = (
            (p.current_location or '') + ' ' + (p.preferred_location or '') + ' ' + combined_resume_text
        ).lower()
        if loc_term and loc_term not in loc_text:
            continue

        # Experience filter
        yrs = p.experience_years or 0
        if not yrs and combined_resume_text and extract_experience_years:
            try:
                yrs = int(extract_experience_years(combined_resume_text))
            except Exception:
                yrs = 0

        if exp_min is not None and yrs < exp_min:
            continue
        if exp_max is not None and yrs > exp_max:
            continue

        # Collect skills for card display
        display_skills = []
        if p.skills:
            display_skills.extend([s.strip() for s in p.skills.split(',') if s.strip()])
        for ja_sk in app_skills_list:
            display_skills.extend([s.strip() for s in ja_sk.split(',') if s.strip()])

        if not display_skills and matched_terms:
            display_skills = [t.title() for t in matched_terms]

        seen_sk = set()
        clean_display_skills = []
        for sk in display_skills:
            sk_lower = sk.lower()
            if sk_lower not in seen_sk:
                seen_sk.add(sk_lower)
                clean_display_skills.append(sk)

        # Candidate resume URL — only the candidate's own registered resume
        resume_url = ''
        if getattr(p, 'resume', None) and p.resume:
            try: resume_url = p.resume.url
            except Exception: pass

        full_name = (user.get_full_name() or user.username).strip()

        seen_emails.add(email_key)
        results.append({
            'name': full_name or 'Candidate',
            'email': user.email or 'Not provided',
            'phone': p.mobile or 'Not provided',
            'location': p.current_location or p.preferred_location or '',
            'experience': f"{yrs}+ Years" if yrs else "Fresher",
            'exp_years': yrs,
            'skills': clean_display_skills[:8],
            'skill_count': skill_count,
            'industry': p.get_industry_display() if p.industry else '',
            'education': p.higher_education_degree or p.iti_diploma_specialization or '',
            'resume_url': resume_url,
        })

    # Fallback to parse folder PDFs if any disk-only resumes match
    if raw_query:
        folder_candidates = parse_resumes_from_folder(raw_query, location_query, exp_query)
        for fc in folder_candidates:
            fc_email = (fc.get('email') or '').strip().lower()
            if fc_email and fc_email != 'not available' and fc_email in seen_emails:
                for res in results:
                    if res.get('email', '').strip().lower() == fc_email:
                        if not res.get('resume_url'):
                            res['resume_url'] = fc.get('resume_url')
                        break
                continue
            results.append(fc)

    results.sort(key=lambda c: (c['skill_count'], c['exp_years']), reverse=True)
    return results


@login_required(login_url='employer_portal:employer_login')
def search_candidates(request):
    """Premium Candidate Search Engine - searches REGISTERED STUDENTS by skills, location, experience."""
    if request.session.get('portal') != 'employer':
        from django.contrib.auth import logout as auth_logout
        auth_logout(request)
        return redirect('job_home')

    query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    experience = request.GET.get('experience', '').strip()

    results = []
    if query or location or experience:
        results = search_registered_candidates(query, location, experience)
    else:
        # Show all candidates if no search filters specified
        results = search_registered_candidates('', '', '')

    return render(request, 'jobs/candidate_search.html', {
        'query': query,
        'location': location,
        'experience': experience,
        'results': results,
    })


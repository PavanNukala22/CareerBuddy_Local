import hashlib

from django.conf import settings
from django.db import models

from core.crypto_fields import EncryptedCharField
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.files.storage import FileSystemStorage


class OverwriteStorage(FileSystemStorage):
    """Storage that overwrites an existing file instead of adding a random suffix."""
    def get_available_name(self, name, max_length=None):
        if self.exists(name):
            self.delete(name)
        return name


def resume_upload_path(instance, filename):
    """One deterministic filename per candidate, so a re-upload overwrites the old one.

    The filename must stay deterministic (same user -> same path, so
    OverwriteStorage replaces rather than duplicates it) but must not be a
    directly guessable function of the public, sequential user id — résumés
    are served from MEDIA_URL with no login check, so a filename like
    "candidate_<id>.pdf" turns that gap into a trivial bulk-download of every
    candidate's résumé by iterating small integers.
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'pdf'
    token = hashlib.sha256(f'resume:{instance.user_id}:{settings.SECRET_KEY}'.encode()).hexdigest()[:20]
    return f'resumes/candidate_{token}.{ext}'


GENDER_CHOICES = [
    ('male',       'Male'),
    ('female',     'Female'),
    ('other',      'Other'),
    ('prefer_not', 'Prefer not to say'),
]

EDUCATION_CHOICES = [
    ('7th',     '7th Standard'),
    ('8th',     '8th Standard'),
    ('9th',     '9th Standard'),
    ('10th',    '10th / SSLC'),
    ('11th',    '11th Standard'),
    ('12th',    '12th / HSC / PUC'),
    ('iti',     'ITI'),
    ('diploma', 'Diploma'),
    ('ug',      'Under-Graduate / Degree'),
    ('pg',      'Post-Graduate'),
]

BLOOD_GROUP_CHOICES = [
    ('A+',  'A+'), ('A-',  'A-'),
    ('B+',  'B+'), ('B-',  'B-'),
    ('AB+', 'AB+'), ('AB-', 'AB-'),
    ('O+',  'O+'), ('O-',  'O-'),
]

INDUSTRY_CHOICES = [
    ('manufacturing', 'Manufacturing'),
    ('it_software',   'IT / Software'),
    ('healthcare',    'Healthcare & Pharma'),
    ('construction',  'Construction & Real Estate'),
    ('retail',        'Retail & FMCG'),
    ('hospitality',   'Hospitality & Tourism'),
    ('education',     'Education & Training'),
    ('finance',       'Finance, Banking & Insurance'),
    ('agriculture',   'Agriculture & Food Processing'),
    ('logistics',     'Logistics & Transportation'),
    ('automobile',    'Automobile & Engineering'),
    ('textile',       'Textile & Garments'),
    ('oil_gas',       'Oil, Gas & Energy'),
    ('government',    'Government / PSU'),
    ('media',         'Media & Entertainment'),
    ('telecom',       'Telecom'),
    ('other',         'Other'),
]

LEVEL_CHOICES = [
    ('beginner',           'Pre-Intermediate'),
    ('intermediate',       'Intermediate'),
    ('upper_intermediate', 'Upper-Intermediate'),
    ('advanced',           'Advanced'),
]

LANGUAGE_PROFICIENCY_CHOICES = [
    ('good',         'Good'),
    ('intermediate', 'Intermediate'),
    ('expert',       'Expert'),
]

ROLE_CHOICES = [
    ('student',    'Student'),
    ('instructor', 'Instructor'),
]


PLAN_CHOICES = [
    ('free',   'Free Plan'),
    ('normal', 'Normal User'),
    ('pro',    'Pro User'),
]

class UserProfile(models.Model):
    user         = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role         = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    english_level = models.CharField(max_length=30, choices=LEVEL_CHOICES, default='intermediate')
    bio          = models.TextField(blank=True)
    avatar       = models.ImageField(upload_to='avatars/', null=True, blank=True)
    is_pro              = models.BooleanField(default=False, help_text='Pro subscription status')
    plan_type           = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free', help_text='Subscription plan type')
    subscription_start  = models.DateTimeField(null=True, blank=True, help_text='When the current paid plan was activated')
    pending_expiry_notice = models.BooleanField(default=False, help_text='Set when a paid plan auto-lapsed to Free; drives the one-time "plan expired" popup')
    joined_at           = models.DateTimeField(auto_now_add=True)

    # ── Subscription helpers ─────────────────────────────────────────────────
    SUBSCRIPTION_DURATION_DAYS = 365  # All paid plans are valid for 1 year

    def subscription_expiry(self):
        """Returns the expiry datetime for the active paid plan, or None if on free plan."""
        from datetime import timedelta
        if self.plan_type == 'free' or not self.subscription_start:
            return None
        return self.subscription_start + timedelta(days=self.SUBSCRIPTION_DURATION_DAYS)

    def is_subscription_active(self):
        """True when the user is on a paid plan whose 1-year window has not yet expired."""
        from django.utils import timezone
        if self.plan_type == 'free':
            return False
        expiry = self.subscription_expiry()
        if expiry is None:
            return False
        return timezone.now() < expiry

    def is_expired(self):
        """True when a paid plan exists but its 1-year window has already passed.

        A paid plan with no subscription_start is handled by enforce_expiry()
        below (which backfills the date rather than treating it as expired) -
        this only reaches "no window to measure" if called before that
        backfill has ever run, so it stays conservative and reports "not
        expired" rather than guessing.
        """
        from django.utils import timezone
        if self.plan_type == 'free':
            return False
        if not self.subscription_start:
            return False
        expiry = self.subscription_expiry()
        return expiry is not None and timezone.now() >= expiry

    def days_until_expiry(self):
        """Whole days left on the active paid plan (0 on the last day), or None on Free.

        Returns a negative number if the plan has already lapsed.
        """
        from django.utils import timezone
        expiry = self.subscription_expiry()
        if expiry is None:
            return None
        return (expiry - timezone.now()).days

    def enforce_expiry(self):
        """Auto-revert a lapsed paid plan to Free. Call this on plan resolution so
        entitlement follows the calendar without a manual downgrade.

        Returns True only on the call that actually performs the downgrade, so the
        caller can raise a one-time 'plan expired' notice.
        """
        from django.utils import timezone

        # A paid plan with no subscription_start is missing bookkeeping, not
        # evidence the plan lapsed - it most likely came from a manual plan
        # change (Django admin, a data import, or a bug elsewhere) that never
        # recorded the date. Treating that gap as automatic expiry silently
        # revokes a real paying user's access, with nothing on their end to
        # fix it. Self-heal instead: backfill the date to now, so the user
        # gets a full fresh term measured from the moment this is noticed,
        # the same way a first purchase would set it.
        if self.plan_type != 'free' and not self.subscription_start:
            self.subscription_start = timezone.now()
            self.save(update_fields=['subscription_start'])
            return False

        if self.is_expired():
            self.plan_type = 'free'
            self.is_pro = False
            self.subscription_start = None
            self.pending_expiry_notice = True   # consumed once by the popup
            self.save(update_fields=['plan_type', 'is_pro', 'subscription_start', 'pending_expiry_notice'])
            return True
        return False

    def can_downgrade_to_free(self):
        """A user may switch to Free only once their paid subscription has run its
        full 1-year term. Manual early downgrades are not allowed (the plan lapses
        automatically at the end of the year via enforce_expiry())."""
        return not self.is_subscription_active()

    # ── Personal Details ────────────────────────────────────────────────────
    gender           = models.CharField(max_length=15, choices=GENDER_CHOICES, blank=True)
    mobile           = models.CharField(max_length=20, blank=True, help_text='Stored in E.164 format, e.g. +919876543210')
    alternate_mobile = models.CharField(max_length=20, blank=True, help_text='Stored in E.164 format, e.g. +919876543210')
    blood_group      = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True)
    languages_known  = models.CharField(
        max_length=300, blank=True,
        help_text='Comma-separated summary of languages known'
    )
    english_proficiency  = models.CharField(max_length=20, choices=LANGUAGE_PROFICIENCY_CHOICES, blank=True)
    hindi_proficiency    = models.CharField(max_length=20, choices=LANGUAGE_PROFICIENCY_CHOICES, blank=True)
    telugu_proficiency   = models.CharField(max_length=20, choices=LANGUAGE_PROFICIENCY_CHOICES, blank=True)
    gujarati_proficiency = models.CharField(max_length=20, choices=LANGUAGE_PROFICIENCY_CHOICES, blank=True)
    other_languages      = models.CharField(max_length=200, blank=True)
    selfie = models.ImageField(upload_to='selfies/', null=True, blank=True)

    # ── Identity Documents ──────────────────────────────────────────────────
    # SR-05 fix: encrypted at rest (see core/crypto_fields.py). max_length here
    # is the ciphertext's storage size, not the plaintext length — plaintext
    # length is still enforced by the form fields in users/forms.py.
    aadhar_number  = EncryptedCharField(max_length=255, blank=True)
    pan_number     = EncryptedCharField(max_length=255, blank=True)
    passport_number = EncryptedCharField(max_length=255, blank=True)

    # ── Education ───────────────────────────────────────────────────────────
    education_level            = models.CharField(max_length=10, choices=EDUCATION_CHOICES, blank=True)
    passed_out_year            = models.PositiveIntegerField(null=True, blank=True)
    iti_diploma_specialization = models.CharField(
        max_length=200, blank=True,
        help_text='Specialization — for ITI / Diploma only'
    )
    higher_education_degree = models.CharField(
        max_length=200, blank=True,
        help_text='Degree name — for UG / PG, e.g. B.Tech, MBA, B.Com, M.Sc'
    )

    # ── Additional Education ─────────────────────────────────────────────────
    education_level_2            = models.CharField(max_length=10, choices=EDUCATION_CHOICES, blank=True)
    passed_out_year_2            = models.PositiveIntegerField(null=True, blank=True)
    iti_diploma_specialization_2 = models.CharField(
        max_length=200, blank=True,
        help_text='Specialization — for ITI / Diploma (2nd entry)'
    )
    higher_education_degree_2 = models.CharField(
        max_length=200, blank=True,
        help_text='Degree name — for UG / PG (2nd entry), e.g. MBA, M.Tech'
    )
    additional_educations_json = models.JSONField(
        default=list, blank=True, null=True,
        help_text='Stores an array of additional education records as JSON'
    )

    # ── Experience & Skills ─────────────────────────────────────────────────
    has_experience        = models.BooleanField(default=False)
    experience_years      = models.PositiveIntegerField(null=True, blank=True, help_text='Years of experience')
    company_name          = models.CharField(max_length=200, blank=True, help_text='Company Name')
    contact_person_role   = models.CharField(max_length=100, blank=True, help_text='Manager / HR Role')
    contact_person_mobile = models.CharField(max_length=20, blank=True, help_text='Manager / HR Mobile Number, stored in E.164 format, e.g. +919876543210')
    contact_person_email  = models.EmailField(max_length=254, blank=True, help_text='Manager / HR Email ID')
    industry              = models.CharField(max_length=30, choices=INDUSTRY_CHOICES, blank=True)
    skills                = models.TextField(blank=True, help_text='Comma-separated skills')
    current_ctc           = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Current CTC in LPA'
    )
    expected_ctc = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Expected CTC in LPA'
    )
    certification = models.CharField(max_length=500, blank=True)
    resume        = models.FileField(
        upload_to=resume_upload_path, storage=OverwriteStorage(),
        null=True, blank=True,
        help_text='Candidate resume (PDF / DOC / DOCX)'
    )
    resume_text   = models.TextField(
        blank=True,
        help_text='Extracted text of the uploaded resume — used for accurate candidate search'
    )

    # ── Location ────────────────────────────────────────────────────────────
    current_location   = models.CharField(max_length=200, blank=True)
    preferred_location = models.CharField(max_length=200, blank=True)

    # ── Abroad Experience ───────────────────────────────────────────────────
    has_abroad_experience = models.BooleanField(default=False)
    abroad_years          = models.PositiveIntegerField(null=True, blank=True)
    abroad_country        = models.CharField(max_length=100, blank=True)
    abroad_industry       = models.CharField(max_length=100, blank=True)
    abroad_skills         = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def update_resume_text(self, save=True):
        """Extract text from the uploaded resume and store it for candidate search."""
        if not self.resume:
            return
        try:
            from career_app.resume_utils import extract_text_from_pdf, extract_text_from_docx
            name = (self.resume.name or '').lower()
            path = self.resume.path
            if name.endswith('.pdf'):
                text = extract_text_from_pdf(path)
            elif name.endswith('.docx'):
                text = extract_text_from_docx(path)
            else:
                text = ''
            if text and not text.lower().startswith('error'):
                self.resume_text = text
                if save:
                    self.save(update_fields=['resume_text'])
        except Exception:
            # Never let resume parsing break registration / profile save
            pass

    def get_total_completed(self):
        return self.user.progress.filter(status='completed').count()

    def get_total_score(self):
        results = self.user.exercise_results.all()
        return sum(r.score for r in results)

    def get_activities_started(self):
        from activities.models import Activity
        started_activity_ids = self.user.progress.filter(
            status__in=['in_progress', 'completed']
        ).values_list('sub_activity__activity_id', flat=True).distinct()
        return Activity.objects.filter(id__in=started_activity_ids).count()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
import hashlib

from django.db import models
from django.conf import settings
from django.core.files.storage import storages
from core.models import Resume, JobDescription


def interview_video_storage():
    return storages['interview_videos']


def interview_video_upload_path(instance, filename):
    """Deterministic, non-guessable filename per interview session.

    Interview recordings are at least as sensitive as the résumé/selfie media
    this app already protects, so the path must not be a guessable function
    of the session's sequential id the way `interview_videos/<id>.webm` would
    be (see resume_upload_path in users/models.py for the same pattern).
    """
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'webm'
    token = hashlib.sha256(f'interview_video:{instance.pk}:{settings.SECRET_KEY}'.encode()).hexdigest()[:20]
    return f'interview_videos/session_{token}.{ext}'


class ResumeInterviewSession(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
    matching_skills = models.JSONField(default=list, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    total_score = models.IntegerField(null=True, blank=True, help_text="Total scaled integer score out of 100")
    is_passed = models.BooleanField(default=False, help_text="True if total_score >= 70")
    # Classified once at interview start from the resume's years of
    # experience (see classify_experience_level in resume_utils.py). Stored
    # explicitly rather than re-derived every time, so the difficulty bounds
    # for this specific interview stay fixed even if resume text is edited
    # mid-interview, and so it's visible on the session record itself.
    experience_level = models.CharField(max_length=20, blank=True, default='')
    # Role picked on the career-path page ({role, dept, track, text, industries},
    # see career_app/role_fit.py). When set, the domain questions come from this
    # role instead of the resume's own domain. Null for interviews without one.
    target_role = models.JSONField(null=True, blank=True)
    # Set server-side only after the client confirms a live camera stream
    # (resume_camera_verified view) — the question/answer endpoints check
    # this directly, so the mandatory-camera requirement is enforced in
    # application logic and not only by the frontend gate screen.
    camera_verified_at = models.DateTimeField(null=True, blank=True)
    interview_video = models.FileField(
        upload_to=interview_video_upload_path, storage=interview_video_storage, null=True, blank=True
    )

    # ── Anti-malpractice tracking ───────────────────────────────────────
    # Server-side counter/status so a page refresh, a new tab, or any other
    # client-side trick can't reset how many violations have already been
    # recorded — resume_record_violation is the only place this is ever
    # incremented, and it always reads/writes the DB row, never trusting a
    # count the client sends.
    MALPRACTICE_CLEAN = 'clean'
    MALPRACTICE_FLAGGED = 'flagged'
    MALPRACTICE_TERMINATED = 'terminated'
    MALPRACTICE_STATUS_CHOICES = [
        (MALPRACTICE_CLEAN, 'Clean'),
        (MALPRACTICE_FLAGGED, 'Flagged for review'),
        (MALPRACTICE_TERMINATED, 'Terminated'),
    ]
    malpractice_violation_count = models.PositiveIntegerField(default=0)
    malpractice_status = models.CharField(max_length=20, choices=MALPRACTICE_STATUS_CHOICES, default=MALPRACTICE_CLEAN)

    @property
    def interview_video_url(self):
        """Access-checked streaming URL for the recording, or '' if there is none.

        Deliberately NOT FileField.url. With the MinIO backend that returns a
        link straight at the object store, which fails twice over: the bucket
        is private and querystring_auth is off, so an unsigned direct link is
        a 403; and it skips the employer-ownership check in core/media_views.py
        entirely. This routes every play through serve_protected_media, which
        reads from whichever storage backend is configured and answers Range
        requests so the player can seek.
        """
        if not self.interview_video:
            return ''
        from django.urls import reverse
        filename = self.interview_video.name.rsplit('/', 1)[-1]
        return reverse('serve_protected_interview_video', args=[filename])

    def __str__(self):
        return f"Interview for Resume {self.resume_id} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"


class ResumeQuestion(models.Model):
    QUESTION_TYPES = [
        ('theory', 'Theory'),
        ('coding', 'Coding'),
    ]

    session = models.ForeignKey(
        ResumeInterviewSession, on_delete=models.CASCADE, related_name='questions'
    )

    question_type = models.CharField(
        max_length=20,
        choices=QUESTION_TYPES,
        default='theory'
    )

    topic = models.CharField(max_length=100)
    question_text = models.TextField()
    difficulty = models.CharField(max_length=20, default='Easy', choices=[('Easy', 'Easy'), ('Intermediate', 'Intermediate'), ('Hard', 'Hard')])
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    # When this question was first served to the client — anchors the 30s
    # answer timer server-side so the deadline can't be reset by re-fetching
    # the question or manipulated from the client.
    presented_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"[{self.topic}] {str(self.question_text)[:50]}"


class ResumeAnswer(models.Model):
    question = models.OneToOneField(
        ResumeQuestion, on_delete=models.CASCADE, related_name='answer'
    )
    text = models.TextField()
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    timed_out = models.BooleanField(default=False, help_text="Answer was auto-submitted because the 30s timer expired")

    def __str__(self):
        return f"Answer to: {str(self.question.question_text)[:50]}"


class InterviewViolation(models.Model):
    """One recorded anti-malpractice event for an interview session.

    Kept as its own table (rather than just the summary counter on
    ResumeInterviewSession) so the full audit trail required by the
    malpractice spec — type, timestamp, duration, running occurrence count —
    survives independently of the session's live counter.
    """
    TYPE_FACE_NOT_DETECTED = 'FACE_NOT_DETECTED'
    TYPE_MULTIPLE_FACES = 'MULTIPLE_FACES'
    TYPE_TAB_SWITCH = 'TAB_SWITCH'
    TYPE_WINDOW_BLUR = 'WINDOW_BLUR'
    TYPE_CAMERA_INTERRUPTED = 'CAMERA_INTERRUPTED'
    TYPE_FULLSCREEN_EXIT = 'FULLSCREEN_EXIT'
    TYPE_COPY_PASTE = 'COPY_PASTE'
    TYPE_SCREENSHOT_ATTEMPT = 'SCREENSHOT_ATTEMPT'
    TYPE_CHOICES = [
        (TYPE_FACE_NOT_DETECTED, 'Face not detected'),
        (TYPE_MULTIPLE_FACES, 'Multiple faces detected'),
        (TYPE_TAB_SWITCH, 'Tab switch'),
        (TYPE_WINDOW_BLUR, 'Window/focus change'),
        (TYPE_CAMERA_INTERRUPTED, 'Camera interrupted'),
        (TYPE_FULLSCREEN_EXIT, 'Fullscreen exit'),
        (TYPE_COPY_PASTE, 'Copy/cut/paste detected'),
        (TYPE_SCREENSHOT_ATTEMPT, 'Screenshot attempt detected'),
    ]

    session = models.ForeignKey(
        ResumeInterviewSession, on_delete=models.CASCADE, related_name='violations'
    )
    violation_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    occurred_at = models.DateTimeField(auto_now_add=True)
    # This type's occurrence count for the session at the moment this row was
    # written (1st, 2nd, 3rd, ...) — lets the log show escalation over time
    # without re-aggregating the whole table.
    occurrence_number = models.PositiveIntegerField(default=1)
    duration_seconds = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['occurred_at']

    def __str__(self):
        return f"[{self.session_id}] {self.violation_type} #{self.occurrence_number}"


class RazorpayPayment(models.Model):
    """
    BUG-02 fix: records every successfully verified Razorpay payment.
    The unique constraint on razorpay_payment_id prevents the same payment
    from being replayed to activate a plan a second time.
    """
    # PAY-P02/P08: a captured payment is not the end of its life — it can be
    # refunded, or captured but impossible to apply. Without a status the ledger
    # cannot tell a good payment from a refunded one, and money owed back to a
    # customer exists only as a log line.
    STATUS_CAPTURED = 'captured'
    STATUS_REFUNDED = 'refunded'
    STATUS_PARTIALLY_REFUNDED = 'partially_refunded'
    STATUS_REFUND_REQUIRED = 'refund_required'
    STATUS_CHOICES = [
        (STATUS_CAPTURED, 'Captured'),
        (STATUS_REFUNDED, 'Refunded'),
        (STATUS_PARTIALLY_REFUNDED, 'Partially refunded'),
        (STATUS_REFUND_REQUIRED, 'Refund required — captured but not applied'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='razorpay_payments',
    )
    razorpay_payment_id = models.CharField(max_length=100, unique=True)
    # Indexed: support searches the ledger by order id during reconciliation.
    razorpay_order_id   = models.CharField(max_length=100, db_index=True)
    # GST tax-invoice serial (e.g. CB/2026-27/00042). A GST invoice needs a
    # unique, immutable, consecutive serial number, so it is stored once at
    # creation rather than derived on the fly — the number on a customer's
    # invoice must never shift if the numbering logic is later changed.
    invoice_number      = models.CharField(max_length=32, blank=True, db_index=True)
    plan_type           = models.CharField(max_length=20)
    amount_paise        = models.PositiveIntegerField()
    # An amount with no currency beside it is a poor basis for reconciliation,
    # even while both payment paths reject anything that is not INR.
    currency            = models.CharField(max_length=8, default='INR')
    status              = models.CharField(max_length=32, choices=STATUS_CHOICES, default=STATUS_CAPTURED)
    refunded_amount_paise = models.PositiveIntegerField(default=0)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} | {self.plan_type} | {self.razorpay_payment_id}"

    @staticmethod
    def financial_year_for(dt):
        """Indian financial year label (Apr 1 – Mar 31) for a datetime, e.g. '2026-27'."""
        if dt.month >= 4:
            start = dt.year
        else:
            start = dt.year - 1
        return f"{start}-{(start + 1) % 100:02d}"

    def assign_invoice_number(self):
        """Stamp a GST invoice serial once, from the (immutable) primary key.

        Deriving the serial from the pk gives a unique, monotonic number without
        a separate counter to race on. Must be called after the row is saved so
        both pk and created_at exist. A no-op if a number was already assigned.
        """
        if self.invoice_number or not self.pk:
            return
        fy = self.financial_year_for(self.created_at)
        self.invoice_number = f"CB/{fy}/{self.pk:05d}"
        self.save(update_fields=['invoice_number'])

    # ── GST tax breakdown (all in rupees) ───────────────────────────────────
    # amount_paise is the gross the customer paid (base + 18% GST). The invoice
    # has to show the taxable value and the tax split it was built from, so the
    # base is recovered from the gross rather than re-read from the price list —
    # a receipt for an order placed at an older price still reconciles.
    @property
    def total_rupees(self):
        return self.amount_paise / 100

    @property
    def taxable_value(self):
        from django.conf import settings
        rate = getattr(settings, 'GST_RATE', 0.18)
        return self.total_rupees / (1 + rate)

    @property
    def gst_rupees(self):
        return self.total_rupees - self.taxable_value

    @property
    def cgst_rupees(self):
        return self.gst_rupees / 2

    @property
    def sgst_rupees(self):
        return self.gst_rupees / 2


class FAQQuestion(models.Model):
    topic = models.CharField(max_length=100)  # normalized lowercase (the skill/subtopic)
    # The broad industry the topic belongs to (e.g. "infrastructure and
    # construction", "it and software"), normalized lowercase. Domain question
    # selection is gated by industry so a Civil-Engineering resume can never be
    # served a Python/IT question just because a generic word like "storage" or
    # "testing" happens to appear in both domains' topic names. Blank for the
    # older CSV imports that had no industry column.
    industry = models.CharField(max_length=120, blank=True, default='', db_index=True)
    question_text = models.CharField(max_length=500)
    difficulty = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = ('topic', 'question_text')

    def __str__(self):
        return f"[{self.topic}] {str(self.question_text)[:50]}"

class ResumeRoleTemplate(models.Model):
    """Admin-editable role data for the manual Resume Builder.

    The built-in roles live in ``career_app/resume_roles.py``. A row here with
    the same slug overrides any non-empty field of that role; a row with a new
    slug adds a new role (the builder renders it with the same reusable form).
    Untick ``is_active`` to hide a role. ``manage.py seed_resume_roles`` copies
    the built-in roles in so they can be edited here.
    """
    CATEGORY_CHOICES = [
        ('it', 'IT'),
        ('tech', 'Non-IT · Technical'),
        ('nt', 'Non-IT · Non-Technical'),
    ]
    ICON_CHOICES = [(k, k) for k in (
        'code', 'chart', 'brain', 'layers', 'bug', 'globe', 'net', 'shield', 'flag', 'gear', 'hat',
        'calc', 'clip', 'people', 'crown', 'search', 'brief', 'trend', 'box', 'cart', 'wallet', 'mega', 'bolt',
    )]
    LINES_HELP = 'One item per line. Leave blank to keep the built-in value.'

    slug = models.SlugField(max_length=80, unique=True,
                            help_text='Matches a built-in role (e.g. "project-manager") or names a new one.')
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    industry = models.CharField(max_length=120, blank=True)
    icon = models.CharField(max_length=20, choices=ICON_CHOICES, default='brief')
    subtitle = models.CharField(max_length=160, blank=True)
    description = models.TextField(blank=True)
    responsibilities = models.TextField(blank=True, help_text=LINES_HELP)
    required_skills = models.TextField(blank=True, help_text=LINES_HELP)
    recommended_skills = models.TextField(blank=True, help_text=LINES_HELP)
    career_path = models.TextField(blank=True, help_text=LINES_HELP)
    certifications = models.TextField(blank=True, help_text=LINES_HELP)
    experience_label = models.CharField(max_length=60, blank=True,
                                        help_text='Heading for the employment section, e.g. "Site Experience".')
    role_fields = models.JSONField(
        default=list, blank=True,
        help_text='Role-specific form fields: [{"label": "Project planning", "options": ["Scheduling", "WBS"]}, …]')
    level_suggestions = models.JSONField(
        default=dict, blank=True,
        help_text='Per experience level ("fresher", "1-3", "3-5", "5+"): '
                  '{"skills": [...], "responsibilities": [...], "projects": [...], "training": [...]}')
    summary_templates = models.JSONField(
        default=dict, blank=True,
        help_text='Per experience level: a list of editable summary templates. Use [placeholders] '
                  'for anything the candidate must fill in.')
    display_order = models.PositiveIntegerField(default=0, help_text='0 keeps the built-in position.')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('display_order', 'title')
        verbose_name = 'Resume builder role'
        verbose_name_plural = 'Resume builder roles'

    def __str__(self):
        return f'{self.title} ({self.get_category_display()})'

class ResumeDraft(models.Model):
    """A resume written in the Create Resume builder, owned by one user.

    ``data`` holds the builder's form state (personal details, summary and the
    repeatable experience / education / project / certification / achievement /
    internship / volunteering / language entries) as normalised by
    ``career_app.create_resume.normalize``; every read and write is scoped to
    ``user`` so a candidate can only ever reach their own resumes.
    """
    MAX_PER_USER = 20

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='resume_drafts')
    title = models.CharField(max_length=120, default='Untitled resume')
    template = models.CharField(max_length=20, default='classic')
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)

    def __str__(self):
        return f'{self.title} ({self.user_id})'

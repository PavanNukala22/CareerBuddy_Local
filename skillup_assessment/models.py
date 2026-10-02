"""
Skill Up Certificate models.

QuizAttempt (new): the real, server-persisted record of every quiz
submission. Previously activities.views.quiz_submit / amcat_submit /
cocubes_submit computed a score and returned it, but never saved anything
and never even knew who the user was -- meaning certification eligibility
had no durable, backend-verifiable source of truth (spec section 17:
"the database/backend must be the source of truth", explicitly NOT
localStorage/session/frontend state). This model is that source of truth;
see activities/views.py for where each submit endpoint now writes to it.

Certificate: now supports any of the ~27 dynamic subjects in
skillup_assessment.subjects.SUBJECTS (previously a fixed 3-choice module
field for english_vocab/aptitude/tech). `choices=` is deliberately NOT set
on `subject` any more -- the valid set is dynamic (spec section 23), so
validity is checked against subjects.is_valid_subject() in view code
instead of a static Django choices list that would need editing by hand
every time a subject is added.
"""
import os
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class QuizAttempt(models.Model):
    """One graded submission of one quiz, for one user. Written by
    activities.views' three submit endpoints immediately after grading,
    whenever the submitting user is authenticated. This is the only
    server-side record of "did this user pass this subject" -- certificate
    eligibility is always computed from this table, never trusted from the
    client (spec section 14).
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    subject = models.CharField(max_length=32, db_index=True)
    score = models.PositiveIntegerField()
    total = models.PositiveIntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "subject"])]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"QuizAttempt({self.user.username}, {self.subject}, {self.score}/{self.total})"

    @property
    def percentage(self):
        return (self.score / self.total * 100) if self.total else 0


def certificate_pdf_path(instance, filename):
    ext = os.path.splitext(filename)[1] or ".pdf"
    return f"certificates/{instance.user_id}/{instance.subject}_{uuid.uuid4().hex[:10]}{ext}"


def generate_certificate_number(subject):
    """A short, human-presentable unique certificate number (spec section 11),
    e.g. CB-PYT-20260911-A1B2C3.
    """
    subject_code = subject[:3].upper()
    date_part = timezone.now().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:6].upper()
    return f"CB-{subject_code}-{date_part}-{random_part}"


class Certificate(models.Model):
    """The certificate record for one user + one subject (one of the ~27 in
    skillup_assessment.subjects.SUBJECTS). Created only once a passing
    QuizAttempt (>=70%) exists for that user+subject AND the user has
    submitted a valid name. Regeneration (changing the name after the
    fact) is an explicit action, never implicit.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skillup_certificates")
    subject = models.CharField(max_length=32, db_index=True)
    certificate_name = models.CharField(max_length=150)

    # Score this certificate was generated against -- a snapshot of the
    # QuizAttempt that made the user eligible at generation time.
    score = models.PositiveIntegerField()
    total = models.PositiveIntegerField(default=100)

    certificate_number = models.CharField(max_length=40, unique=True, blank=True)
    pdf_file = models.FileField(upload_to=certificate_pdf_path, null=True, blank=True)
    is_generated = models.BooleanField(default=False)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "subject"], name="one_certificate_per_user_per_subject"),
        ]

    def __str__(self):
        return f"Certificate({self.user.username}, {self.subject}, '{self.certificate_name}')"

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = generate_certificate_number(self.subject)
        super().save(*args, **kwargs)

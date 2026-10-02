from django.db import models
from django.conf import settings


class ScoreRecord(models.Model):
    """Shared score record used by GD, JAM, and other workshop modules."""
    MODULE_CHOICES = [
        ('gd', 'Group Discussion'),
        ('jam', 'JAM'),
        ('roleplay', 'Role Play'),
        ('speaking', 'Speaking'),
        ('writing', 'Writing'),
        ('listening', 'Listening'),
        ('reading', 'Reading'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='score_records'
    )
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    score = models.FloatField(default=0)
    max_score = models.FloatField(default=25)
    label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} | {self.module} | {self.score}/{self.max_score}"


class Resume(models.Model):
    """Uploaded resume files (used by Employer Portal candidate search)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="resumes",
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to='resumes/')
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resume {self.id} – {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"


class JobDescription(models.Model):
    """Job description text (used by Employer Portal)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="job_descriptions",
        null=True,
        blank=True,
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"JD {self.id} – {self.created_at.strftime('%Y-%m-%d %H:%M')}"

from django.db import models
from django.contrib.auth.models import User


class Topic(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        default='medium'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['title']


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='jam_profile')
    bio = models.TextField(blank=True)
    avatar_initial = models.CharField(max_length=2, blank=True)
    total_sessions = models.IntegerField(default=0)
    total_minutes = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        if not self.avatar_initial and self.user.username:
            self.avatar_initial = self.user.username[0].upper()
        super().save(*args, **kwargs)


class JAMSession(models.Model):
    SCORE_CHOICES = [
        (1, 'Level 1'), (2, 'Level 2'),
        (3, 'Level 3'), (4, 'Level 4'), (5, 'Level 5'),
    ]
    CONFIDENCE_CHOICES = [
        (1, '⭐ Nervous'), (2, '⭐⭐ Unsure'),
        (3, '⭐⭐⭐ Okay'), (4, '⭐⭐⭐⭐ Confident'), (5, '⭐⭐⭐⭐⭐ Great!'),
    ]
    FLUENCY_CHOICES = [
        (1, '⭐ Many pauses'), (2, '⭐⭐ Some pauses'),
        (3, '⭐⭐⭐ Moderate'), (4, '⭐⭐⭐⭐ Mostly fluent'), (5, '⭐⭐⭐⭐⭐ Very fluent'),
    ]
    LANGUAGE_CHOICES = [
        (1, '⭐ Basic'), (2, '⭐⭐ Limited'),
        (3, '⭐⭐⭐ Adequate'), (4, '⭐⭐⭐⭐ Good'), (5, '⭐⭐⭐⭐⭐ Excellent'),
    ]
    PRONUNCIATION_CHOICES = [
        (1, '⭐ Unclear'), (2, '⭐⭐ Needs work'),
        (3, '⭐⭐⭐ Acceptable'), (4, '⭐⭐⭐⭐ Clear'), (5, '⭐⭐⭐⭐⭐ Native-like'),
    ]
    TIME_CHOICES = [
        (1, '⭐ Very short'), (2, '⭐⭐ Too brief'),
        (3, '⭐⭐⭐ Moderate'), (4, '⭐⭐⭐⭐ Good use'), (5, '⭐⭐⭐⭐⭐ Perfect'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, related_name='sessions')
    audio_file = models.FileField(upload_to='audio/', blank=True, null=True)
    duration = models.IntegerField(default=0, help_text='Duration in seconds')

    # Self-evaluation scores (5 categories)
    confidence_score = models.IntegerField(choices=CONFIDENCE_CHOICES, null=True, blank=True)
    fluency_score = models.IntegerField(choices=FLUENCY_CHOICES, null=True, blank=True)
    language_score = models.IntegerField(choices=LANGUAGE_CHOICES, null=True, blank=True)
    pronunciation_score = models.IntegerField(choices=PRONUNCIATION_CHOICES, null=True, blank=True)
    time_management_score = models.IntegerField(choices=TIME_CHOICES, null=True, blank=True)

    notes = models.TextField(blank=True, help_text='Personal notes about the session')
    transcript = models.TextField(blank=True, help_text='Transcribed text from the session')
    language = models.CharField(
        max_length=20, default='english', blank=True,
        help_text="Language chosen in the header dropdown when the session was recorded. "
                  "Feedback is generated in this language.",
    )
    ai_feedback = models.TextField(blank=True, help_text='AI-generated feedback')
    improvement_tips = models.TextField(blank=True, help_text='Actionable improvement roadmap')
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.topic} ({self.created_at.date()})"

    class Meta:
        ordering = ['-created_at']

    @property
    def duration_display(self):
        minutes = self.duration // 60
        seconds = self.duration % 60
        if minutes:
            return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    @property
    def average_score(self):
        scores = [s for s in [
            self.confidence_score, self.fluency_score,
            self.language_score, self.pronunciation_score,
            self.time_management_score
        ] if s is not None]
        if scores:
            return round(sum(scores) / len(scores), 1)
        return None

    @property
    def overall_score_display(self):
        scores = [s for s in [
            self.confidence_score, self.fluency_score,
            self.language_score, self.pronunciation_score,
            self.time_management_score
        ] if s is not None]
        if scores:
            return sum(scores)
        return None


class AssessmentGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessments')
    easy_session = models.OneToOneField(JAMSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessment_easy')
    medium_session = models.OneToOneField(JAMSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessment_medium')
    hard_session = models.OneToOneField(JAMSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='assessment_hard')
    final_report = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Assessment for {self.user.username} ({self.created_at.date()})"

    class Meta:
        ordering = ['-created_at']

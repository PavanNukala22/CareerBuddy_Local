from django.db import models
from django.conf import settings

class GDSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='gd_sessions', null=True)
    topic = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    performance_report = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"GD: {self.topic[:50]} | {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class GDMessage(models.Model):
    SPEAKER_CHOICES = [
        ('user', 'User'),
        ('alex', 'Alex (Analytical)'),
        ('maya', 'Maya (Creative)'),
        ('rishi', 'Rishi (Moderator)'),
    ]

    session = models.ForeignKey(GDSession, on_delete=models.CASCADE, related_name='messages')
    speaker = models.CharField(max_length=20, choices=SPEAKER_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_user = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.speaker}] {self.content[:60]}"

    @property
    def color(self):
        colors = {
            'alex': '#4F8EF7',
            'maya': '#C471ED',
            'rishi': '#43E97B',
            'user': '#F59E0B'
        }
        return colors.get(self.speaker, '#F59E0B')

    @property
    def bg_color(self):
        return f"{self.color}18"

    @property
    def avatar(self):
        avatars = {
            'alex': '🔵',
            'maya': '🟣',
            'rishi': '🟢',
            'user': '🧑'
        }
        return avatars.get(self.speaker, '🧑')

from django.db import models
from django.conf import settings

class Resume(models.Model):
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


class ResumeInterviewSession(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
    matching_skills = models.JSONField(default=list, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Interview for Resume {self.resume_id} – {self.start_time.strftime('%Y-%m-%d %H:%M')}"


class ResumeQuestion(models.Model):
    session = models.ForeignKey(
        ResumeInterviewSession, on_delete=models.CASCADE, related_name='questions'
    )
    topic = models.CharField(max_length=100)
    question_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"[{self.topic}] {self.question_text[:50]}"


class ResumeAnswer(models.Model):
    question = models.OneToOneField(
        ResumeQuestion, on_delete=models.CASCADE, related_name='answer'
    )
    text = models.TextField()
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer to: {self.question.question_text[:50]}"


class FAQQuestion(models.Model):
    topic = models.CharField(max_length=100)  # normalized lowercase
    question_text = models.CharField(max_length=500)
    difficulty = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = ('topic', 'question_text')

    def __str__(self):
        return f"[{self.topic}] {self.question_text[:50]}"

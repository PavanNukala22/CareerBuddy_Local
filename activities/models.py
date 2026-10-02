from django.db import models
from django.contrib.auth.models import User
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from django.db.models.query import QuerySet
from django.utils import timezone


CATEGORY_CHOICES = [
    ('speaking', 'Speaking & Presentation'),
    ('writing', 'Writing & Correspondence'),
    ('vocabulary', 'Vocabulary & Idioms'),
    ('negotiation', 'Negotiation & Meetings'),
    ('communication', 'Professional Communication'),
    ('analysis', 'Analysis & Reporting'),
    ('workshop', 'Interactive Workshop'),
]

EXERCISE_TYPE_CHOICES = [
    ('mcq', 'Multiple Choice'),
    ('fill_blank', 'Fill in the Blank'),
    ('matching', 'Matching'),
    ('ordering', 'Ordering'),
    ('bingo', 'Vocabulary Bingo'),
    ('writing', 'Writing Submission'),
    ('timer', 'Timed Activity'),
]


class Activity(models.Model):
    if TYPE_CHECKING:
        subactivities: 'QuerySet[SubActivity]'

    order = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    level = models.CharField(max_length=100)
    duration = models.CharField(max_length=50)
    materials = models.TextField()
    objective = models.TextField()
    icon_class = models.CharField(max_length=100, default='fas fa-book')
    color_class = models.CharField(max_length=50, default='primary')
    is_active = models.BooleanField(default=True)
    objects = models.Manager()

    class Meta:
        ordering = ['order']

    def __str__(self) -> str:
        return f"Activity {self.order}: {self.title}"

    def get_progress(self, user):
        """Performance-based progress — see activities/progress.py."""
        from .progress import progress_for_activity, EMPTY
        if not user.is_authenticated:
            return EMPTY
        return progress_for_activity(user, self)

    def get_completion_rate(self, user):
        """Kept for existing callers: now the performance percentage (0-100),
        not the share of sub-activities opened."""
        return self.get_progress(user).percent



class SubActivity(models.Model):
    if TYPE_CHECKING:
        exercises: 'QuerySet[Exercise]'

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='subactivities')
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructions = models.TextField()
    objects = models.Manager()

    class Meta:
        ordering = ['order']
        unique_together = ['activity', 'order']

    def __str__(self) -> str:
        return f"{self.activity.title} - Sub {self.order}: {self.title}"

    def all_exercises_done(self, user):
        """True only once the user has a result for every exercise here.

        A sub-activity must not read as "completed" just because the user
        submitted one exercise out of several — see UserProgress.mark_completed
        callers, which rely on this before flipping status to 'completed'.
        """
        exercise_ids = list(self.exercises.values_list('id', flat=True))
        if not exercise_ids:
            return False
        done_ids = set(
            UserExerciseResult.objects.filter(
                user=user, exercise_id__in=exercise_ids
            ).values_list('exercise_id', flat=True).distinct()
        )
        return done_ids.issuperset(exercise_ids)


class Exercise(models.Model):
    if TYPE_CHECKING:
        questions: 'QuerySet[Question]'

    sub_activity = models.ForeignKey(SubActivity, on_delete=models.CASCADE, related_name='exercises')
    title = models.CharField(max_length=200)
    exercise_type = models.CharField(max_length=30, choices=EXERCISE_TYPE_CHOICES)
    instructions = models.TextField()
    order = models.PositiveIntegerField(default=1)
    objects = models.Manager()

    class Meta:
        ordering = ['order']

    def __str__(self) -> str:
        return f"{self.sub_activity} - {self.title}"


class Question(models.Model):
    if TYPE_CHECKING:
        question_text: str

    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='questions')
    order = models.PositiveIntegerField()
    question_text = models.TextField() # type: ignore
    option_a = models.CharField(max_length=300, blank=True)
    option_b = models.CharField(max_length=300, blank=True)
    option_c = models.CharField(max_length=300, blank=True)
    option_d = models.CharField(max_length=300, blank=True)
    correct_answer = models.CharField(max_length=300)
    explanation = models.TextField(blank=True)
    left_item = models.CharField(max_length=200, blank=True)
    right_item = models.CharField(max_length=200, blank=True)
    objects = models.Manager()

    class Meta:
        ordering = ['order']

    def __str__(self) -> str:
        return f"Q{self.order}: {self.question_text[:60]}"


class BingoCard(models.Model):
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='bingo_cards')
    word = models.CharField(max_length=100)
    definition = models.TextField()
    objects = models.Manager()

    def __str__(self) -> str:
        return str(self.word)


class FreeActivitySelection(models.Model):
    """
    An activity selected by a Free Plan user.

    Free users can access up to five activities from the Free Plan
    activity pool. Each selected activity remains accessible, while
    other activities stay locked.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='free_activity_selections',
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.CASCADE,
        related_name='free_selections',
    )
    started_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'activity'],
                name='unique_free_activity_selection',
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.username} → {self.activity.title}"


class UserProgress(models.Model):
    if TYPE_CHECKING:
        user: User
        sub_activity: 'SubActivity'
        status: str
        started_at: Optional[timezone.datetime]
        completed_at: Optional[timezone.datetime]

    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='progress') # type: ignore
    sub_activity = models.ForeignKey(SubActivity, on_delete=models.CASCADE) # type: ignore
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started') # type: ignore
    started_at = models.DateTimeField(null=True, blank=True) # type: ignore
    completed_at = models.DateTimeField(null=True, blank=True) # type: ignore
    objects = models.Manager()

    class Meta:
        unique_together = ['user', 'sub_activity']

    def __str__(self):
        return f"{self.user.username} - {self.sub_activity} [{self.status}]"

    def mark_started(self):
        if self.status == 'not_started':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save()

    def mark_completed(self):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if not self.started_at:
            self.started_at = self.completed_at
        self.save()


class UserExerciseResult(models.Model):
    if TYPE_CHECKING:
        user: User
        exercise: 'Exercise'
        score: int
        max_score: int
        completed_at: timezone.datetime

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exercise_results') # type: ignore
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE) # type: ignore
    score = models.PositiveIntegerField(default=0) # type: ignore
    max_score = models.PositiveIntegerField(default=0) # type: ignore
    answers_json = models.JSONField(default=dict)
    result_data = models.JSONField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True) # type: ignore
    attempt_number = models.PositiveIntegerField(default=1)
    objects = models.Manager()

    class Meta:
        ordering = ['-completed_at']

    def __str__(self) -> str:
        return f"{self.user.username} - {self.exercise.title} ({self.score}/{self.max_score})"

    @property
    def percentage(self):
        if self.max_score == 0:
            return 0
        return int((self.score / self.max_score) * 100)

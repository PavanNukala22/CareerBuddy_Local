from django.contrib import admin
from .models import (
    Activity, SubActivity, Exercise, Question, BingoCard,
    UserProgress, UserExerciseResult, FreeActivitySelection,
)


class SubActivityInline(admin.TabularInline):
    model = SubActivity
    extra = 0
    fields = ['order', 'title', 'description']
    ordering = ['order']


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ['order', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_answer']


class BingoCardInline(admin.TabularInline):
    model = BingoCard
    extra = 0
    fields = ['word', 'definition']


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 0
    fields = ['order', 'title', 'exercise_type']


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['order', 'title', 'category', 'level', 'duration', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'objective']
    ordering = ['order']
    inlines = [SubActivityInline]


@admin.register(SubActivity)
class SubActivityAdmin(admin.ModelAdmin):
    list_display = ['activity', 'order', 'title']
    list_filter = ['activity']
    search_fields = ['title', 'description']
    ordering = ['activity__order', 'order']
    inlines = [ExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['sub_activity', 'title', 'exercise_type', 'order']
    list_filter = ['exercise_type']
    search_fields = ['title']
    inlines = [QuestionInline, BingoCardInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exercise', 'order', 'question_text', 'correct_answer']
    search_fields = ['question_text']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'sub_activity', 'status', 'started_at', 'completed_at']
    list_filter = ['status']
    search_fields = ['user__username']


@admin.register(FreeActivitySelection)
class FreeActivitySelectionAdmin(admin.ModelAdmin):
    """Delete a row here to give a Free Plan user their single activity choice back."""
    list_display = ['user', 'activity', 'started_at']
    search_fields = ['user__username', 'activity__title']
    autocomplete_fields = ['activity']


@admin.register(UserExerciseResult)
class UserExerciseResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'exercise', 'score', 'max_score', 'percentage', 'completed_at']
    list_filter = ['completed_at']
    search_fields = ['user__username']

    def percentage(self, obj):
        return f"{obj.percentage}%"

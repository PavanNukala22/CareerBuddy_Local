from django.contrib import admin
from .models import Topic, UserProfile, JAMSession, AssessmentGroup


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'is_active', 'created_at', 'session_count']
    list_filter = ['difficulty', 'is_active']
    search_fields = ['title', 'description']
    list_editable = ['is_active', 'difficulty']

    def session_count(self, obj):
        return obj.sessions.count()
    session_count.short_description = 'Sessions'


@admin.register(JAMSession)
class JAMSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'duration_display', 'confidence_score', 'fluency_score', 'completed', 'created_at']
    list_filter = ['completed', 'created_at', 'confidence_score']
    search_fields = ['user__username', 'topic__title']
    readonly_fields = ['created_at']

    def duration_display(self, obj):
        return obj.duration_display
    duration_display.short_description = 'Duration'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_sessions', 'total_minutes']
    search_fields = ['user__username']

@admin.register(AssessmentGroup)
class AssessmentGroupAdmin(admin.ModelAdmin):
    list_display = ['user', 'completed', 'created_at']
    list_filter = ['completed', 'created_at']
    search_fields = ['user__username']

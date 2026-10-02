from django.contrib import admin

from .models import Certificate, QuizAttempt


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "subject", "certificate_name", "score", "total",
        "certificate_number", "is_generated", "generated_at",
    )
    list_filter = ("subject", "is_generated")
    search_fields = ("user__username", "certificate_name", "certificate_number")
    readonly_fields = ("certificate_number", "created_at", "updated_at")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "subject", "score", "total", "submitted_at")
    list_filter = ("subject",)
    search_fields = ("user__username",)
    readonly_fields = ("submitted_at",)

from django.contrib import admin

from .models import RazorpayPayment, ResumeInterviewSession, InterviewViolation


class InterviewViolationInline(admin.TabularInline):
    model = InterviewViolation
    extra = 0
    can_delete = False
    fields = ('violation_type', 'occurrence_number', 'duration_seconds', 'occurred_at')
    readonly_fields = fields
    ordering = ('occurred_at',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ResumeInterviewSession)
class ResumeInterviewSessionAdmin(admin.ModelAdmin):
    """Lets a reviewer actually act on the 'flagged for review' status the
    anti-malpractice system sets — without this there's a status on the row
    but nowhere to see it. Read-only: nothing here is meant to be hand-edited.
    """
    list_display = ('id', 'resume_user', 'start_time', 'total_score', 'is_passed',
                     'malpractice_status', 'malpractice_violation_count', 'is_completed')
    list_filter = ('malpractice_status', 'is_passed', 'is_completed')
    search_fields = ('resume__user__username', 'resume__user__email')
    ordering = ('-start_time',)
    inlines = [InterviewViolationInline]
    readonly_fields = (
        'resume', 'job_description', 'start_time', 'is_completed', 'total_score',
        'is_passed', 'experience_level', 'camera_verified_at', 'interview_video',
        'malpractice_violation_count', 'malpractice_status',
    )

    @admin.display(description='Candidate', ordering='resume__user__username')
    def resume_user(self, obj):
        return getattr(obj.resume.user, 'username', None) or obj.resume_id

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RazorpayPayment)
class RazorpayPaymentAdmin(admin.ModelAdmin):
    """Read-only ledger of verified payments, for support and reconciliation.

    Rows mirror what Razorpay captured, so they are never created or edited by
    hand — every field is read-only and adding is disabled.
    """
    list_display = ('created_at', 'user', 'plan_type', 'amount_rupees', 'status',
                    'razorpay_payment_id')
    # status is filterable so support can pull every payment that still owes the
    # customer money — "refund required" is no longer only a log line (PAY-P08).
    list_filter = ('status', 'plan_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'razorpay_payment_id', 'razorpay_order_id')
    # No date_hierarchy: it compiles to CONVERT_TZ(), which returns NULL on a
    # MySQL server without the timezone tables loaded (mysql_tzinfo_to_sql) and
    # takes the whole ledger page down with it. The created_at list filter gives
    # the same date narrowing without the timezone dependency.
    ordering = ('-created_at',)
    readonly_fields = (
        'user', 'plan_type', 'amount_paise', 'currency', 'status',
        'refunded_amount_paise', 'razorpay_payment_id', 'razorpay_order_id',
        'created_at', 'updated_at',
    )

    @admin.display(description='Amount', ordering='amount_paise')
    def amount_rupees(self, obj):
        return f'₹{obj.amount_paise / 100:.2f}'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

"""
Subscription-notice context processor.

Exposes, on every template, the flags that drive the site-wide subscription
popup: a one-time "plan expired" notice when a paid plan auto-lapses to Free,
and a renewal reminder during the final 7 days of an active plan.

Scope: payment / subscription only. Adds template variables, changes no view.
"""


def subscription_notice(request):
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    # Staff / superusers are treated as Pro everywhere and never expire.
    if user.is_staff or user.is_superuser:
        return {}

    profile = getattr(user, 'profile', None)
    if profile is None:
        return {}

    # Make sure a lapsed plan is reverted before we read its state.
    profile.enforce_expiry()

    # One-time "your plan expired and was moved to Free" popup.
    if getattr(profile, 'pending_expiry_notice', False):
        profile.pending_expiry_notice = False
        profile.save(update_fields=['pending_expiry_notice'])
        return {'sub_show_expired': True}

    # Renewal reminder in the final week of an active paid plan.
    if profile.is_subscription_active():
        days = profile.days_until_expiry()
        if days is not None and 0 <= days <= 7:
            return {
                'sub_show_warning': True,
                'sub_days_left': days,
                'sub_plan_label': profile.get_plan_type_display() if hasattr(profile, 'get_plan_type_display') else profile.plan_type.title(),
                'sub_expiry_date': profile.subscription_expiry(),
            }

    return {}

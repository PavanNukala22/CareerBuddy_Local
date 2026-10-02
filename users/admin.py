from django import forms
from django.contrib import admin
from django.utils import timezone

from .models import UserProfile


class UserProfileAdminForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # is_pro mirrors plan_type and is maintained by the payment code. Editing
        # it by hand used to create a profile that resolved as Pro with no paid
        # plan behind it, which no expiry check could revoke — so it is hidden.
        exclude = ['is_pro']

    def clean_subscription_start(self):
        """PAY-P11: refuse a start date in the future.

        Every expiry check derives from subscription_start + 365 days, so a
        future date pushes the expiry past a year and leaves entitlement that
        enforce_expiry() can never take back — one mistyped year in this field
        grants two, a mis-pasted value grants a decade.

        Only operator edits are checked. A renewal legitimately parks the start
        date in the future (it becomes the current expiry, which is how the
        second year stacks), and that profile must stay editable for every other
        field.
        """
        value = self.cleaned_data.get('subscription_start')
        if value and 'subscription_start' in self.changed_data and value > timezone.now():
            raise forms.ValidationError(
                'Subscription start cannot be in the future — it would grant '
                'entitlement that no expiry check can revoke.'
            )
        return value


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ['user', 'role', 'english_level', 'plan_type', 'subscription_start', 'joined_at']
    list_filter = ['role', 'english_level', 'plan_type']
    search_fields = ['user__username', 'user__email']

    def save_model(self, request, obj, form, change):
        """Keep a hand-granted plan consistent with the subscription rules.

        A paid plan with no start date has no 1-year window, so the expiry check
        treats it as already lapsed. Anchoring it here means granting a plan from
        the admin does what the operator expects: a full year from today, unless
        they set a start date themselves.
        """
        if obj.plan_type != 'free' and not obj.subscription_start:
            obj.subscription_start = timezone.now()
        if obj.plan_type == 'free':
            obj.subscription_start = None
        obj.is_pro = (obj.plan_type == 'pro')
        super().save_model(request, obj, form, change)

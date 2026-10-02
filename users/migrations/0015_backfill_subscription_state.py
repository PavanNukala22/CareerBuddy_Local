"""Repair subscription rows that predate the current plan fields.

Two states exist in older data, both of which hand out entitlement that the
expiry system cannot see:

1. `is_pro=True, plan_type='free'` — profiles upgraded before `plan_type` was
   added (0008). Plan resolution used to honour the `is_pro` flag on its own, so
   these users are Pro today; without this backfill they would silently drop to
   Free the moment resolution stops trusting that flag.
2. `plan_type` paid but `subscription_start=NULL` — profiles upgraded before
   `subscription_start` was added (0013). Their plans never expire.

Anchoring (2) to the migration time gives those users a full year from here.
Their real purchase dates were never recorded, so the alternatives are to guess
or to cut them off early; a fresh year is the only option that cannot take away
something a user already paid for. Adjust individual rows in the admin if you
have payment dates to reconcile against.
"""
from django.db import migrations
from django.utils import timezone


def backfill(apps, schema_editor):
    UserProfile = apps.get_model('users', 'UserProfile')
    now = timezone.now()

    # 1. Legacy Pro flag with no plan_type behind it.
    UserProfile.objects.filter(is_pro=True, plan_type='free').update(plan_type='pro')

    # 2. Paid plan with no start date — anchor it so the 1-year window exists.
    UserProfile.objects.exclude(plan_type='free').filter(
        subscription_start__isnull=True
    ).update(subscription_start=now)

    # 3. Keep the derived flag consistent with the plan it mirrors.
    UserProfile.objects.filter(plan_type='pro', is_pro=False).update(is_pro=True)
    UserProfile.objects.exclude(plan_type='pro').filter(is_pro=True).update(is_pro=False)


def noop(apps, schema_editor):
    """Nothing to undo — the repaired rows are the correct state."""


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_userprofile_pending_expiry_notice'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]

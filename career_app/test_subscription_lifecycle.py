"""
Subscription lifecycle tests — early-downgrade block, auto-expiry, and the
7-day renewal / expiry notices. Run: python manage.py test career_app
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from activities.views import _has_full_activities_access
from career_app.views import _get_user_plan
from career_app.context_processors import subscription_notice

User = get_user_model()


def _mk(user, plan, days_ago):
    p = user.profile
    p.plan_type = plan
    p.is_pro = (plan == 'pro')
    p.subscription_start = timezone.now() - timedelta(days=days_ago)
    p.pending_expiry_notice = False
    p.save()
    return p


class DowngradeBlockTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u1', 'u1@x.com', 'pw12345!')
        self.client.force_login(self.user)

    def test_cannot_downgrade_before_one_year(self):
        _mk(self.user, 'pro', days_ago=100)      # 100 days in — still active
        self.client.post(reverse('toggle_pro_status'), {'plan_type': 'free'})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'pro')   # NOT downgraded

    def test_can_downgrade_after_expiry(self):
        _mk(self.user, 'pro', days_ago=400)      # past 1 year
        # enforce_expiry (via resolution) will already move it to free
        self.assertEqual(_get_user_plan(self.user), 'free')


class AutoExpiryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u2', 'u2@x.com', 'pw12345!')

    def test_active_plan_resolves_paid(self):
        _mk(self.user, 'pro', days_ago=10)
        self.assertEqual(_get_user_plan(self.user), 'pro')

    def test_expired_plan_auto_reverts_to_free(self):
        _mk(self.user, 'pro', days_ago=366)
        self.assertEqual(_get_user_plan(self.user), 'free')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')
        self.assertFalse(self.user.profile.is_pro)
        self.assertTrue(self.user.profile.pending_expiry_notice)   # popup flag armed


class ActivitiesAccessTests(TestCase):
    """Full Activities access is an entitlement, so it must follow the same
    expiry rules as every other paid feature."""

    def setUp(self):
        self.user = User.objects.create_user('u4', 'u4@x.com', 'pw12345!')

    def test_active_plan_has_full_access(self):
        _mk(self.user, 'normal', days_ago=10)
        self.assertTrue(_has_full_activities_access(self.user))

    def test_expired_plan_loses_full_access(self):
        _mk(self.user, 'pro', days_ago=400)
        self.assertFalse(_has_full_activities_access(self.user))


class UnanchoredPlanTests(TestCase):
    """A paid plan with no start date is missing bookkeeping (e.g. a manual
    admin change), not a lapsed plan. enforce_expiry() self-heals it by starting
    the 1-year window now, so the plan can still expire — it never becomes
    permanent Pro."""

    def setUp(self):
        self.user = User.objects.create_user('u5', 'u5@x.com', 'pw12345!')

    def test_paid_plan_without_start_date_gets_a_window(self):
        p = self.user.profile
        p.plan_type = 'pro'
        p.is_pro = True
        p.subscription_start = None
        p.save()
        before = timezone.now()
        self.assertEqual(_get_user_plan(self.user), 'pro')
        self.user.profile.refresh_from_db()
        self.assertIsNotNone(self.user.profile.subscription_start)
        self.assertGreaterEqual(self.user.profile.subscription_start, before)
        self.assertIsNotNone(self.user.profile.subscription_expiry())

    def test_is_pro_flag_alone_grants_nothing(self):
        """is_pro mirrors plan_type; on its own it is not an entitlement."""
        p = self.user.profile
        p.plan_type = 'free'
        p.is_pro = True
        p.subscription_start = None
        p.save()
        self.assertEqual(_get_user_plan(self.user), 'free')
        self.assertFalse(_has_full_activities_access(self.user))


class RenewalWindowTests(TestCase):
    """Renewal is offered only in the last week of an active plan — the same
    window that raises the expiry notice, so the notice's 'renew now' button
    lands on a page that can act on it."""

    def setUp(self):
        self.user = User.objects.create_user('u6', 'u6@x.com', 'pw12345!')
        self.client.force_login(self.user)

    def _page(self):
        return self.client.get(reverse('pro_page'))

    def test_no_renew_button_mid_term(self):
        _mk(self.user, 'pro', days_ago=100)
        resp = self._page()
        self.assertFalse(resp.context['renewal_window'])
        self.assertNotContains(resp, 'Renew for another year')

    def test_renew_button_in_final_week(self):
        _mk(self.user, 'pro', days_ago=360)          # 5 days left
        resp = self._page()
        self.assertTrue(resp.context['renewal_window'])
        self.assertContains(resp, 'Renew for another year')

    def test_no_renew_button_on_free_plan(self):
        _mk(self.user, 'pro', days_ago=400)          # lapsed to free
        resp = self._page()
        self.assertFalse(resp.context['renewal_window'])
        self.assertNotContains(resp, 'Renew for another year')

    def test_window_matches_the_notice_window(self):
        """Both are driven by the same 7-day boundary; if one moves the other
        must move with it, or the notice goes back to being a dead end."""
        _mk(self.user, 'normal', days_ago=359)
        self.assertTrue(self._page().context['renewal_window'])
        self.assertTrue(subscription_notice(_Req(self.user)).get('sub_show_warning'))


class _Req:
    def __init__(self, user):
        self.user = user


class NoticeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('u3', 'u3@x.com', 'pw12345!')

    def _ctx(self):
        class R:  # minimal request stub
            user = self.user
        return subscription_notice(R())

    def test_warning_within_7_days(self):
        _mk(self.user, 'normal', days_ago=360)   # 5 days left
        ctx = self._ctx()
        self.assertTrue(ctx.get('sub_show_warning'))
        self.assertLessEqual(ctx.get('sub_days_left'), 7)

    def test_no_warning_when_plenty_left(self):
        _mk(self.user, 'normal', days_ago=100)
        ctx = self._ctx()
        self.assertFalse(ctx.get('sub_show_warning', False))

    def test_expired_popup_shows_once(self):
        _mk(self.user, 'pro', days_ago=400)
        first = self._ctx()
        self.assertTrue(first.get('sub_show_expired'))
        second = self._ctx()                     # flag already consumed
        self.assertFalse(second.get('sub_show_expired', False))

    def test_staff_never_notified(self):
        self.user.is_staff = True
        self.user.save()
        _mk(self.user, 'pro', days_ago=400)
        self.assertEqual(self._ctx(), {})

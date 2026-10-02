"""Every customer money-path transition, end to end.

One test per way a customer's money and entitlement can move. The rule these
enforce: money captured must always produce either entitlement or a ledger row
that says money is owed back. It must never vanish.

Run: python manage.py test career_app.test_payment_transitions
"""
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from career_app.models import RazorpayPayment
from career_app.views import _get_user_plan, _plan_amount_paise
from users.models import UserProfile

User = get_user_model()
DAY = timedelta(days=1)


def order(plan, user_id, amount=None, currency='INR', status='paid', quoted=True):
    notes = {'plan': plan, 'user_id': str(user_id)}
    if quoted:
        notes['amount_paise'] = str(_plan_amount_paise(plan))
    return {'id': 'order_T', 'amount': amount if amount is not None else _plan_amount_paise(plan),
            'currency': currency, 'status': status, 'notes': notes}


def client_for(order_dict, sig_ok=True):
    c = MagicMock()
    if sig_ok:
        c.utility.verify_payment_signature.return_value = True
    else:
        c.utility.verify_payment_signature.side_effect = Exception('bad sig')
    c.order.fetch.return_value = order_dict
    return c


@override_settings(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='s',
                   RAZORPAY_WEBHOOK_SECRET='whsec')
class TransitionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cust', 'cust@x.com', 'pw12345!')
        self.client.force_login(self.user)

    # ── helpers ────────────────────────────────────────────────────────────
    def pay(self, plan, order_dict=None, payment_id='pay_1', sig_ok=True, posted=None):
        fake = client_for(order_dict or order(plan, self.user.id), sig_ok)
        with patch('career_app.views._razorpay_client', return_value=fake):
            return self.client.post(reverse('verify_razorpay_payment'), {
                'plan_type': posted or plan,
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': 'order_T',
                'razorpay_signature': 'sig',
            })

    def webhook(self, plan, payment_id='pay_wh'):
        body = json.dumps({'event': 'payment.captured', 'payload': {'payment': {'entity': {
            'id': payment_id, 'order_id': 'order_T', 'amount': _plan_amount_paise(plan),
            'currency': 'INR', 'notes': {},
        }}}}).encode()
        sig = hmac.new(b'whsec', body, hashlib.sha256).hexdigest()
        fake = MagicMock()
        fake.order.fetch.return_value = {'notes': {
            'plan': plan, 'user_id': str(self.user.id),
            'amount_paise': str(_plan_amount_paise(plan))}}
        with patch('career_app.views._razorpay_client', return_value=fake):
            return self.client.post(reverse('razorpay_webhook'), data=body,
                                    content_type='application/json',
                                    headers={'x-razorpay-signature': sig})

    def profile(self):
        return UserProfile.objects.get(user=self.user)

    def plan(self):
        return _get_user_plan(User.objects.get(pk=self.user.pk))

    def set_plan(self, plan, days_ago):
        p = self.profile()
        p.plan_type, p.is_pro = plan, (plan == 'pro')
        p.subscription_start = timezone.now() - timedelta(days=days_ago)
        p.save()
        return p

    def assert_no_money_lost(self, payment_id='pay_1'):
        """A captured payment must leave either entitlement or a ledger row."""
        self.assertTrue(
            RazorpayPayment.objects.filter(razorpay_payment_id=payment_id).exists(),
            'captured payment left no trace: it cannot be reconciled or refunded')

    # ── 1. first purchase ──────────────────────────────────────────────────
    def test_free_to_normal(self):
        self.assertTrue(self.pay('normal').json()['success'])
        self.assertEqual(self.plan(), 'normal')
        self.assertAlmostEqual(self.profile().days_until_expiry(), 364, delta=1)

    def test_free_to_pro(self):
        self.assertTrue(self.pay('pro').json()['success'])
        self.assertEqual(self.plan(), 'pro')

    # ── 2. upgrade ─────────────────────────────────────────────────────────
    def test_upgrade_normal_to_pro_starts_fresh_year(self):
        """Customer paid for a full year of Normal and upgrades on day 100.
        The old plan is retired outright: Pro grants exactly one fresh year
        from today, not a year stacked on top of the unused Normal days."""
        self.set_plan('normal', days_ago=100)
        self.assertTrue(self.pay('pro').json()['success'])
        self.assertEqual(self.plan(), 'pro')
        self.assertAlmostEqual(self.profile().days_until_expiry(), 365, delta=2)

    # ── 3. downgrade while active ──────────────────────────────────────────
    def test_downgrade_blocked_but_payment_recorded(self):
        self.set_plan('pro', days_ago=10)
        resp = self.pay('normal')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.plan(), 'pro')
        self.assert_no_money_lost()
        self.assertEqual(RazorpayPayment.objects.get(razorpay_payment_id='pay_1').status,
                         RazorpayPayment.STATUS_REFUND_REQUIRED)
        self.assertIn('refund', resp.json()['error'].lower())

    # ── 4. renewal ─────────────────────────────────────────────────────────
    def test_same_tier_renewal_stacks(self):
        self.set_plan('pro', days_ago=360)
        before = self.profile().subscription_expiry()
        self.assertTrue(self.pay('pro').json()['success'])
        self.assertAlmostEqual((self.profile().subscription_expiry() - before).days, 365, delta=1)

    def test_repurchase_after_expiry_starts_fresh(self):
        self.set_plan('normal', days_ago=400)
        self.assertEqual(self.plan(), 'free')           # lapsed
        self.assertTrue(self.pay('normal').json()['success'])
        self.assertAlmostEqual(self.profile().days_until_expiry(), 364, delta=1)

    # ── 5. browser closed / webhook ────────────────────────────────────────
    def test_browser_closed_webhook_activates(self):
        self.assertEqual(self.webhook('pro').json()['status'], 'ok')
        self.assertEqual(self.plan(), 'pro')

    def test_callback_then_webhook_grants_one_year_only(self):
        self.assertTrue(self.pay('pro', payment_id='pay_wh').json()['success'])
        expiry = self.profile().subscription_expiry()
        self.assertEqual(self.webhook('pro', payment_id='pay_wh').json()['status'],
                         'already_processed')
        self.assertEqual(self.profile().subscription_expiry(), expiry)

    # ── 6. money captured, confirmation impossible ─────────────────────────
    def test_razorpay_unreachable_reports_pending_not_failure(self):
        fake = client_for(order('pro', self.user.id))
        fake.order.fetch.side_effect = Exception('connection reset')
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self.client.post(reverse('verify_razorpay_payment'), {
                'plan_type': 'pro', 'razorpay_payment_id': 'pay_1',
                'razorpay_order_id': 'order_T', 'razorpay_signature': 'sig'})
        body = resp.json()
        self.assertTrue(body['pending'])
        self.assertNotIn('failed', body['error'].lower())
        self.assertEqual(self.plan(), 'free')           # webhook will finish it

    def test_uncaptured_order_reports_pending_and_grants_nothing(self):
        resp = self.pay('pro', order('pro', self.user.id, status='attempted'))
        self.assertTrue(resp.json()['pending'])
        self.assertEqual(self.plan(), 'free')

    # ── 7. misconfiguration hitting a genuine payer ────────────────────────
    def test_amount_mismatch_on_own_order_is_recorded(self):
        """The order belongs to this user and the signature is valid, so the
        money is real. The amount disagreeing means our side is misconfigured —
        the customer must still be reconcilable."""
        bad = order('pro', self.user.id, amount=_plan_amount_paise('pro') - 5000)
        resp = self.pay('pro', bad)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.plan(), 'free')
        self.assert_no_money_lost()

    def test_currency_mismatch_on_own_order_is_recorded(self):
        bad = order('pro', self.user.id, currency='USD')
        resp = self.pay('pro', bad)
        self.assertEqual(resp.status_code, 400)
        self.assert_no_money_lost()

    # ── 8. attacks must NOT be recorded against us ─────────────────────────
    def test_bad_signature_grants_nothing(self):
        resp = self.pay('pro', sig_ok=False)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.plan(), 'free')

    def test_other_users_order_grants_nothing(self):
        resp = self.pay('pro', order('pro', 99999))
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.plan(), 'free')
        self.assertFalse(RazorpayPayment.objects.filter(user=self.user).exists())

    def test_client_plan_tamper_follows_the_order(self):
        self.assertTrue(self.pay('normal', posted='pro').json()['success'])
        self.assertEqual(self.plan(), 'normal')

    def test_replay_blocked(self):
        self.pay('normal')
        self.assertEqual(self.pay('normal').status_code, 400)
        self.assertEqual(RazorpayPayment.objects.filter(razorpay_payment_id='pay_1').count(), 1)

    # ── 9. refunds ─────────────────────────────────────────────────────────
    def _refund(self, amount, payment_id='pay_1'):
        body = json.dumps({'event': 'refund.processed', 'payload': {'refund': {'entity': {
            'id': 'rfnd_1', 'payment_id': payment_id, 'amount': amount}}}}).encode()
        sig = hmac.new(b'whsec', body, hashlib.sha256).hexdigest()
        return self.client.post(reverse('razorpay_webhook'), data=body,
                                content_type='application/json',
                                headers={'x-razorpay-signature': sig})

    def test_full_refund_revokes_entitlement(self):
        self.pay('pro')
        self.assertEqual(self.plan(), 'pro')
        self.assertTrue(self._refund(_plan_amount_paise('pro')).json()['full_refund'])
        self.assertEqual(self.plan(), 'free')

    def test_partial_refund_keeps_entitlement(self):
        self.pay('pro')
        self._refund(1000)
        self.assertEqual(self.plan(), 'pro')
        self.assertEqual(RazorpayPayment.objects.get(razorpay_payment_id='pay_1').status,
                         RazorpayPayment.STATUS_PARTIALLY_REFUNDED)

"""
PAY-01 regression tests — plan/amount must be bound to the ACTUAL paid order,
not to the client-supplied plan_type. Run: python manage.py test career_app
"""
import hashlib
import hmac
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from career_app.views import _get_user_plan

from career_app import views
from career_app.models import RazorpayPayment
from career_app.views import _activate_plan, _plan_amount_paise
from users.models import UserProfile

User = get_user_model()

_UNSET = object()


def _activate(user, plan, days_ago):
    """Put `user` on a paid plan that started `days_ago` days back."""
    p = user.profile
    p.plan_type = plan
    p.is_pro = (plan == 'pro')
    p.subscription_start = timezone.now() - timedelta(days=days_ago)
    p.save()
    return p


def _fake_client(order_notes_plan, order_user_id, order_amount, sig_ok=True,
                 quoted_amount=_UNSET, currency='INR'):
    client = MagicMock()
    if sig_ok:
        client.utility.verify_payment_signature.return_value = True
    else:
        client.utility.verify_payment_signature.side_effect = Exception("bad sig")
    notes = {'plan': order_notes_plan, 'user_id': str(order_user_id)}
    if quoted_amount is not _UNSET:
        notes['amount_paise'] = str(quoted_amount)
    client.order.fetch.return_value = {
        'id': 'order_TEST',
        'amount': order_amount,
        'currency': currency,
        'notes': notes,
    }
    return client


@override_settings(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='secret')
class VerifyPaymentSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('stud', 'stud@x.com', 'pw12345!')
        self.client.force_login(self.user)
        self.url = reverse('verify_razorpay_payment')

    def _post(self, plan):
        return self.client.post(self.url, {
            'plan_type': plan,
            'razorpay_payment_id': 'pay_1',
            'razorpay_order_id': 'order_TEST',
            'razorpay_signature': 'sig',
        })

    def test_plan_tamper_no_escalation(self):
        """Paid for NORMAL, posts PRO -> entitlement follows the ORDER, never
        the client. User gets NORMAL (what they paid for), never PRO."""
        fake = _fake_client('normal', self.user.id, _plan_amount_paise('normal'))
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self._post('pro')            # tampered client input
        self.user.profile.refresh_from_db()
        # Must NOT be elevated to pro under any circumstance.
        self.assertNotEqual(self.user.profile.plan_type, 'pro')
        # Server binds to the paid order -> normal.
        self.assertEqual(self.user.profile.plan_type, 'normal')
        self.assertEqual(resp.json()['plan_type'], 'normal')

    def test_legitimate_normal_activates(self):
        fake = _fake_client('normal', self.user.id, _plan_amount_paise('normal'))
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self._post('normal')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'normal')

    def test_order_belongs_to_other_user_blocked(self):
        fake = _fake_client('pro', 99999, _plan_amount_paise('pro'))  # someone else's order
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self._post('pro')
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')

    def test_bad_signature_blocked(self):
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'), sig_ok=False)
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self._post('pro')
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')

    def test_replay_blocked(self):
        fake = _fake_client('normal', self.user.id, _plan_amount_paise('normal'))
        with patch('career_app.views._razorpay_client', return_value=fake):
            self._post('normal')              # first: succeeds
            resp = self._post('normal')       # second: same payment_id -> replay
        self.assertEqual(resp.status_code, 400)

    def test_downgrade_while_active_blocked(self):
        """Pro subscriber paying for Normal must not be pulled down a tier."""
        _activate(self.user, 'pro', days_ago=10)
        fake = _fake_client('normal', self.user.id, _plan_amount_paise('normal'))
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self._post('normal')
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'pro')

    def test_refused_payment_is_still_recorded(self):
        """The money was captured before we could refuse it, so it has to appear
        in the ledger — otherwise the user is charged with nothing on file to
        refund against."""
        _activate(self.user, 'pro', days_ago=10)
        fake = _fake_client('normal', self.user.id, _plan_amount_paise('normal'))
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self._post('normal')
        self.assertEqual(resp.status_code, 400)
        payment = RazorpayPayment.objects.get(razorpay_payment_id='pay_1')
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.amount_paise, _plan_amount_paise('normal'))
        self.assertIn('refund', resp.json()['error'].lower())   # user is told, not just logged

    def test_same_plan_renewal_stacks_remaining_term(self):
        """Renewing early adds a year on top of the time left — it never resets
        the clock to now, which used to be impossible anyway (same-tier
        purchases were rejected, so the 'Renew now' notice led nowhere)."""
        profile = _activate(self.user, 'pro', days_ago=360)
        old_expiry = profile.subscription_expiry()
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'))
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self._post('pro')
        self.assertTrue(resp.json()['success'])
        self.user.profile.refresh_from_db()
        new_expiry = self.user.profile.subscription_expiry()
        self.assertAlmostEqual((new_expiry - old_expiry).days, 365, delta=1)


@override_settings(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='secret')
class OrderBindingTests(TestCase):
    """Verification must judge a payment against the order it belongs to, not
    against whatever the price list happens to say at verify time."""

    def setUp(self):
        self.user = User.objects.create_user('bind', 'bind@x.com', 'pw12345!')
        self.client.force_login(self.user)
        self.url = reverse('verify_razorpay_payment')

    def _post(self, plan, fake, payment_id='pay_b1'):
        with patch('career_app.views._razorpay_client', return_value=fake):
            return self.client.post(self.url, {
                'plan_type': plan,
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': 'order_TEST',
                'razorpay_signature': 'sig',
            })

    def test_order_quoted_at_an_old_price_still_verifies(self):
        """A price change while the customer is on the checkout screen must not
        strand the payment they just made."""
        old_price = 41300                                  # what the order was quoted at
        fake = _fake_client('normal', self.user.id, old_price, quoted_amount=old_price)
        resp = self._post('normal', fake)
        self.assertTrue(resp.json()['success'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'normal')

    def test_amount_below_the_quote_is_still_rejected(self):
        fake = _fake_client('pro', self.user.id, 100, quoted_amount=_plan_amount_paise('pro'))
        resp = self._post('pro', fake)
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')

    def test_non_inr_order_rejected(self):
        """Same number, cheaper currency — the amount check alone wouldn't catch it."""
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'), currency='USD')
        resp = self._post('pro', fake)
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')

    def test_bad_client_plan_value_does_not_discard_a_real_payment(self):
        """PAY-P12: the client's plan_type is overwritten by the order's, so
        rejecting it early only threw away genuine captures — money taken, 400
        returned, nothing recorded."""
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'))
        resp = self._post('platinum', fake)              # mangled client field
        self.assertTrue(resp.json()['success'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'pro')      # order decides
        self.assertTrue(RazorpayPayment.objects.filter(razorpay_payment_id='pay_b1').exists())

    def test_uncaptured_order_reports_pending_and_grants_nothing(self):
        """PAY-P04: a signature proves the payment is genuine, not captured."""
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'))
        fake.order.fetch.return_value = {
            **fake.order.fetch.return_value, 'status': 'attempted',
        }
        resp = self._post('pro', fake)
        self.assertTrue(resp.json()['pending'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')

    def test_paid_order_activates(self):
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'))
        fake.order.fetch.return_value = {**fake.order.fetch.return_value, 'status': 'paid'}
        self.assertTrue(self._post('pro', fake).json()['success'])

    def test_unreachable_razorpay_reports_pending_not_failure(self):
        """The signature already proved the payment is real, so the money is
        gone — the user must not be told it failed."""
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'))
        fake.order.fetch.side_effect = Exception('connection reset')
        resp = self._post('pro', fake)
        body = resp.json()
        self.assertFalse(body['success'])
        self.assertTrue(body['pending'])
        self.assertNotIn('failed', body['error'].lower())

    def test_activation_failure_leaves_no_blocking_payment_row(self):
        """The payment row is what blocks a replay, so it must roll back with a
        failed activation — otherwise the retry is refused and the webhook skips
        it, stranding a paid user on Free."""
        fake = _fake_client('pro', self.user.id, _plan_amount_paise('pro'))
        with patch('career_app.views._activate_plan', side_effect=Exception('db down')):
            with self.assertRaises(Exception):
                self._post('pro', fake)
        self.assertFalse(RazorpayPayment.objects.filter(razorpay_payment_id='pay_b1').exists())
        # ...so the retry can go through and actually activate the plan.
        resp = self._post('pro', fake)
        self.assertTrue(resp.json()['success'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'pro')


@override_settings(RAZORPAY_WEBHOOK_SECRET='whsec')
class RefundTests(TestCase):
    """PAY-P02: a refunded customer must not keep the plan they were refunded
    for, and the ledger must be able to tell a refunded payment from a good one."""

    def setUp(self):
        self.user = User.objects.create_user('ref', 'ref@x.com', 'pw12345!')
        self.url = reverse('razorpay_webhook')

    def _pay_row(self, plan='pro', payment_id='pay_ref', status=RazorpayPayment.STATUS_CAPTURED):
        return RazorpayPayment.objects.create(
            user=self.user, razorpay_payment_id=payment_id, razorpay_order_id='order_ref',
            plan_type=plan, amount_paise=_plan_amount_paise(plan), status=status,
        )

    def _fresh_user(self):
        """Re-read the user so plan resolution sees the profile the view wrote,
        not the instance cached on this test's object."""
        return User.objects.get(pk=self.user.pk)

    def _fresh_profile(self):
        return UserProfile.objects.get(user=self.user)

    def _refund(self, amount, payment_id='pay_ref', event='refund.processed'):
        body = json.dumps({
            'event': event,
            'payload': {'refund': {'entity': {
                'id': 'rfnd_1', 'payment_id': payment_id, 'amount': amount,
            }}},
        }).encode()
        sig = hmac.new(b'whsec', body, hashlib.sha256).hexdigest()
        return self.client.post(self.url, data=body, content_type='application/json',
                                headers={'x-razorpay-signature': sig})

    def test_full_refund_revokes_the_year(self):
        _activate(self.user, 'pro', days_ago=10)
        self._pay_row()
        resp = self._refund(_plan_amount_paise('pro'))
        self.assertTrue(resp.json()['full_refund'])
        self.assertEqual(RazorpayPayment.objects.get(razorpay_payment_id='pay_ref').status,
                         RazorpayPayment.STATUS_REFUNDED)
        # The paid year is pulled back, so plan resolution lapses them to Free.
        self.assertEqual(_get_user_plan(self._fresh_user()), 'free')

    def test_full_refund_of_a_stacked_renewal_keeps_the_year_still_paid_for(self):
        """Two payments, one refunded — the customer keeps the year they still
        paid for rather than losing the whole subscription."""
        p = self.user.profile
        p.plan_type, p.is_pro = 'pro', True
        p.subscription_start = timezone.now() + timedelta(days=300)   # stacked renewal
        p.save()
        self._pay_row()
        self._refund(_plan_amount_paise('pro'))
        self.assertEqual(_get_user_plan(self._fresh_user()), 'pro')
        self.assertGreater(self._fresh_profile().days_until_expiry(), 0)

    def test_partial_refund_records_but_does_not_revoke(self):
        _activate(self.user, 'pro', days_ago=10)
        self._pay_row()
        resp = self._refund(1000)
        self.assertFalse(resp.json()['full_refund'])
        row = RazorpayPayment.objects.get(razorpay_payment_id='pay_ref')
        self.assertEqual(row.status, RazorpayPayment.STATUS_PARTIALLY_REFUNDED)
        self.assertEqual(row.refunded_amount_paise, 1000)
        self.assertEqual(_get_user_plan(self._fresh_user()), 'pro')   # entitlement untouched

    def test_refund_of_never_applied_payment_touches_no_entitlement(self):
        _activate(self.user, 'pro', days_ago=10)
        expiry_before = self.user.profile.subscription_expiry()
        self._pay_row(plan='normal', status=RazorpayPayment.STATUS_REFUND_REQUIRED)
        self._refund(_plan_amount_paise('normal'))
        self.assertEqual(self._fresh_profile().subscription_expiry(), expiry_before)

    def test_refund_for_unknown_payment_is_acknowledged(self):
        resp = self._refund(500, payment_id='pay_nope')
        self.assertEqual(resp.json()['status'], 'unknown_payment')

    def test_repeat_refund_event_is_idempotent(self):
        _activate(self.user, 'pro', days_ago=10)
        self._pay_row()
        self._refund(_plan_amount_paise('pro'))
        state_after_first = (self._fresh_profile().plan_type,
                             self._fresh_profile().subscription_start)
        resp = self._refund(_plan_amount_paise('pro'))
        self.assertEqual(resp.json()['status'], 'already_refunded')
        self.assertEqual((self._fresh_profile().plan_type,
                          self._fresh_profile().subscription_start), state_after_first,
                         'a repeated refund event must not take a second year')


@override_settings(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='secret')
class OrderThrottleTests(TestCase):
    """PAY-P06: unthrottled order creation burns Razorpay quota and fills the
    dashboard with abandoned orders."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('thr', 'thr@x.com', 'pw12345!')
        self.client.force_login(self.user)
        self.addCleanup(cache.clear)

    def test_order_creation_is_throttled_per_user(self):
        fake = MagicMock()
        fake.order.create.return_value = {'id': 'order_T'}
        with patch('career_app.views._razorpay_client', return_value=fake):
            codes = [self.client.post(reverse('create_razorpay_order'),
                                      {'plan_type': 'normal'}).status_code
                     for _ in range(views.ORDER_RATE_LIMIT_PER_MINUTE + 2)]
        self.assertEqual(codes[0], 200)
        self.assertEqual(codes[-1], 429)
        self.assertLessEqual(fake.order.create.call_count, views.ORDER_RATE_LIMIT_PER_MINUTE)


class ScopedWriteTests(TestCase):
    """Activation must touch only the subscription columns. UserProfile carries
    the whole candidate record, so a full save() pushes back every field the
    instance was loaded with — reverting edits made in the meantime."""

    def test_activation_does_not_clobber_concurrent_profile_edits(self):
        user = User.objects.create_user('conc', 'conc@x.com', 'pw12345!')
        stale = UserProfile.objects.get(user=user)        # the payment path's handle
        # A concurrent request saves an unrelated field after that fetch.
        UserProfile.objects.filter(pk=stale.pk).update(current_location='Hyderabad')

        _activate_plan(stale, 'pro')

        fresh = UserProfile.objects.get(pk=stale.pk)
        self.assertEqual(fresh.plan_type, 'pro')                  # activation landed
        self.assertEqual(fresh.current_location, 'Hyderabad')     # edit survived


@override_settings(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='secret',
                   DEFAULT_FROM_EMAIL='billing@careerbuddy.test')
class ReceiptEmailTests(TestCase):
    """A successful payment must leave the user with a receipt — the on-screen
    message alone disappears on the next page load."""

    def setUp(self):
        self.user = User.objects.create_user('buyer', 'buyer@x.com', 'pw12345!')
        self.client.force_login(self.user)

    def _pay(self, plan='normal', payment_id='pay_r1'):
        fake = _fake_client(plan, self.user.id, _plan_amount_paise(plan))
        with patch('career_app.views._razorpay_client', return_value=fake):
            return self.client.post(reverse('verify_razorpay_payment'), {
                'plan_type': plan,
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': 'order_TEST',
                'razorpay_signature': 'sig',
            })

    def test_receipt_sent_on_successful_payment(self):
        self._pay()
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, ['buyer@x.com'])
        self.assertIn('Normal User Plan', msg.subject)
        self.assertIn('pay_r1', msg.body)                              # payment reference
        self.assertIn(f'{_plan_amount_paise("normal") / 100:.2f}', msg.body)   # total incl. GST

    def test_no_receipt_when_payment_rejected(self):
        """A failed verification must not tell the user they paid."""
        fake = _fake_client('normal', 99999, _plan_amount_paise('normal'))   # someone else's order
        with patch('career_app.views._razorpay_client', return_value=fake):
            self.client.post(reverse('verify_razorpay_payment'), {
                'plan_type': 'normal',
                'razorpay_payment_id': 'pay_r2',
                'razorpay_order_id': 'order_TEST',
                'razorpay_signature': 'sig',
            })
        self.assertEqual(len(mail.outbox), 0)

    def test_mail_failure_never_breaks_activation(self):
        """The money is already taken by this point — a dead SMTP server must
        not turn a successful payment into an error."""
        with patch('career_app.views.send_transactional_email', side_effect=Exception('smtp down')):
            resp = self._pay()
        self.assertTrue(resp.json()['success'])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'normal')

    def test_user_without_email_still_activates(self):
        self.user.email = ''
        self.user.save()
        resp = self._pay()
        self.assertTrue(resp.json()['success'])
        self.assertEqual(len(mail.outbox), 0)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'normal')


@override_settings(RAZORPAY_WEBHOOK_SECRET='whsec')
class WebhookTests(TestCase):
    """The webhook activates plans without the browser, so it needs the same
    tier guard as the frontend verify call: Razorpay retries a capture for up
    to 24h and can deliver it after the user has already upgraded."""

    def setUp(self):
        self.user = User.objects.create_user('hook', 'hook@x.com', 'pw12345!')
        self.url = reverse('razorpay_webhook')

    def _capture(self, plan, payment_id='pay_hook', notes=_UNSET, order_id='order_hook',
                 order_notes=_UNSET, amount=None):
        """Post a signed payment.captured event.

        `notes` are the payment entity's (browser-supplied); `order_notes` are
        what Razorpay returns for the order (server-created, authoritative).
        """
        if notes is _UNSET:
            notes = {'user_id': str(self.user.id), 'plan': plan}
        if order_notes is _UNSET:
            order_notes = {
                'user_id': str(self.user.id), 'plan': plan,
                'amount_paise': str(_plan_amount_paise(plan)),
            }
        body = json.dumps({
            'event': 'payment.captured',
            'payload': {'payment': {'entity': {
                'id': payment_id,
                'order_id': order_id,
                'amount': _plan_amount_paise(plan) if amount is None else amount,
                'currency': 'INR',
                'notes': notes,
            }}},
        }).encode()
        sig = hmac.new(b'whsec', body, hashlib.sha256).hexdigest()
        fake = MagicMock()
        fake.order.fetch.return_value = {'notes': order_notes}
        with patch('career_app.views._razorpay_client', return_value=fake):
            resp = self.client.post(
                self.url, data=body, content_type='application/json',
                headers={'x-razorpay-signature': sig},
            )
        self.last_fake = fake
        return resp

    def test_forged_payment_notes_cannot_buy_a_higher_plan(self):
        """Payment-entity notes are whatever the browser passed to Checkout, so a
        user can pay for Normal while claiming plan='pro' — and, since orders now
        carry their price in notes, claim a matching amount too. Entitlement must
        follow the ORDER, which only the server can create."""
        normal_price = _plan_amount_paise('normal')
        resp = self._capture(
            'normal',
            notes={'user_id': str(self.user.id), 'plan': 'pro',
                   'amount_paise': str(normal_price)},      # forged, matches what they paid
        )
        self.assertEqual(resp.json()['status'], 'ok')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'normal')   # never 'pro'
        self.assertEqual(RazorpayPayment.objects.get(razorpay_payment_id='pay_hook').plan_type,
                         'normal')

    def test_underpaid_capture_rejected(self):
        resp = self._capture('pro', amount=_plan_amount_paise('normal'))
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')

    def test_capture_activates_plan(self):
        resp = self._capture('pro')
        self.assertEqual(resp.json()['status'], 'ok')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'pro')
        # The browser-close path still owes the user a receipt.
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['hook@x.com'])

    def test_ignored_downgrade_sends_no_receipt(self):
        _activate(self.user, 'pro', days_ago=10)
        self._capture('normal')
        self.assertEqual(len(mail.outbox), 0)

    def test_late_capture_cannot_downgrade_active_plan(self):
        profile = _activate(self.user, 'pro', days_ago=10)
        expiry_before = profile.subscription_expiry()
        resp = self._capture('normal')                  # stale/retried Normal capture
        self.assertEqual(resp.json()['status'], 'ignored_downgrade')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'pro')
        # ...and the 1-year clock must not restart either.
        self.assertEqual(self.user.profile.subscription_expiry(), expiry_before)
        # The payment is still recorded, so it can never be replayed later.
        self.assertTrue(RazorpayPayment.objects.filter(razorpay_payment_id='pay_hook').exists())

    def test_callback_committing_mid_webhook_grants_only_one_year(self):
        """PAY-P01: the callback and the webhook race on every transaction.

        The interleaving that matters is the callback committing its payment row
        *between* the webhook's exists() check and its get_or_create — both fire
        within milliseconds of the same capture, so the window is hit routinely.
        The sequential path was always correct; this one used to stack a second
        year onto a single payment.
        """
        _activate(self.user, 'pro', days_ago=0)          # callback activated the plan
        expiry_before = self.user.profile.subscription_expiry()

        real_get_user_plan = views._get_user_plan

        def callback_wins_the_race(user):
            # Runs after the webhook's exists() check, before its get_or_create.
            RazorpayPayment.objects.get_or_create(
                razorpay_payment_id='pay_hook',
                defaults={
                    'user': self.user, 'razorpay_order_id': 'order_hook',
                    'plan_type': 'pro', 'amount_paise': _plan_amount_paise('pro'),
                },
            )
            return real_get_user_plan(user)

        with patch('career_app.views._get_user_plan', side_effect=callback_wins_the_race):
            resp = self._capture('pro')

        self.assertEqual(resp.json()['status'], 'already_processed')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.subscription_expiry(), expiry_before,
                         'one payment must not grant a second subscription year')
        self.assertEqual(RazorpayPayment.objects.filter(razorpay_payment_id='pay_hook').count(), 1)

    def test_bad_signature_rejected(self):
        resp = self.client.post(
            self.url, data=b'{}', content_type='application/json',
            headers={'x-razorpay-signature': 'nope'},
        )
        self.assertEqual(resp.status_code, 400)

    def test_empty_notes_resolved_from_the_order(self):
        """Razorpay sends notes as [] when the payment carries none, and order
        notes are not guaranteed to reach the payment entity. The plan must then
        come off the order rather than the event being dropped (or 500ing on
        [].get)."""
        resp = self._capture('normal', notes=[])
        self.assertEqual(resp.json()['status'], 'ok')
        self.last_fake.order.fetch.assert_called_once_with('order_hook')
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'normal')

    def test_unresolvable_notes_rejected_cleanly(self):
        """No notes and no order to fall back on -> a 400, never a 500."""
        resp = self._capture('normal', notes=[], order_id='')
        self.assertEqual(resp.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.plan_type, 'free')


@override_settings(RAZORPAY_KEY_ID='rzp_test_x', RAZORPAY_KEY_SECRET='secret',
                   DEFAULT_FROM_EMAIL='billing@careerbuddy.test',
                   COMPANY_LEGAL_NAME='Career Buddy Pvt Ltd', COMPANY_GSTIN='29ABCDE1234F1Z5',
                   COMPANY_STATE='Karnataka', COMPANY_STATE_CODE='29', COMPANY_SAC_CODE='999293')
class GstInvoiceTests(TestCase):
    """A paid subscription must produce a GST tax invoice the customer can view
    (§34.3 gap): a stored serial, the tax split, and access limited to the owner."""

    def setUp(self):
        self.user = User.objects.create_user('buyer', 'buyer@x.com', 'pw12345!')
        self.client.force_login(self.user)

    def _pay(self, plan='normal', payment_id='pay_inv1'):
        fake = _fake_client(plan, self.user.id, _plan_amount_paise(plan))
        with patch('career_app.views._razorpay_client', return_value=fake):
            return self.client.post(reverse('verify_razorpay_payment'), {
                'plan_type': plan,
                'razorpay_payment_id': payment_id,
                'razorpay_order_id': 'order_TEST',
                'razorpay_signature': 'sig',
            })

    def test_invoice_number_assigned_on_payment(self):
        self._pay()
        payment = RazorpayPayment.objects.get(razorpay_payment_id='pay_inv1')
        self.assertTrue(payment.invoice_number)
        self.assertIn(f'{payment.pk:05d}', payment.invoice_number)

    def test_tax_breakdown_sums_to_total(self):
        self._pay()
        p = RazorpayPayment.objects.get(razorpay_payment_id='pay_inv1')
        # base + CGST + SGST must reconstruct the gross the customer paid.
        recomposed = p.taxable_value + p.cgst_rupees + p.sgst_rupees
        self.assertAlmostEqual(recomposed, p.total_rupees, places=2)
        self.assertAlmostEqual(p.cgst_rupees, p.sgst_rupees, places=6)

    def test_owner_can_view_invoice(self):
        self._pay()
        p = RazorpayPayment.objects.get(razorpay_payment_id='pay_inv1')
        resp = self.client.get(reverse('payment_invoice', args=[p.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'TAX INVOICE')
        self.assertContains(resp, p.invoice_number)
        self.assertContains(resp, '29ABCDE1234F1Z5')          # seller GSTIN
        self.assertContains(resp, '999293')                    # SAC code

    def test_other_user_cannot_view_invoice(self):
        self._pay()
        p = RazorpayPayment.objects.get(razorpay_payment_id='pay_inv1')
        other = User.objects.create_user('intruder', 'i@x.com', 'pw12345!')
        self.client.force_login(other)
        resp = self.client.get(reverse('payment_invoice', args=[p.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_receipt_email_links_to_invoice(self):
        self._pay()
        p = RazorpayPayment.objects.get(razorpay_payment_id='pay_inv1')
        self.assertEqual(len(mail.outbox), 1)
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn('View GST Invoice', html)
        self.assertIn(p.invoice_number, html)

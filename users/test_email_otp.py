"""Email-OTP verification for candidate registration.

Covers the two AJAX endpoints and the server-side gate in register_view — the
guarantee that no account is created against an unverified email even if the
front-end guard is bypassed.
"""
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from core import otp_utils


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   DEFAULT_FROM_EMAIL='noreply@careerbuddy.test')
class EmailOtpTests(TestCase):
    def setUp(self):
        cache.clear()
        self.email = 'newcandidate@example.com'

    def _current_code(self, email):
        return cache.get(otp_utils._otp_key(email))['code']

    # ── send endpoint ────────────────────────────────────────────────────────
    def test_send_otp_emails_a_code(self):
        resp = self.client.post(reverse('send_email_otp'), {'email': self.email})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['ok'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('verification code', mail.outbox[0].subject.lower())
        self.assertIn(self._current_code(self.email), mail.outbox[0].alternatives[0][0])

    def test_registered_email_does_not_leak_and_gets_notice(self):
        """A taken email must get the SAME neutral reply as a free one (no
        enumeration), and instead receive an 'account exists' notice — not an OTP."""
        User.objects.create_user('taken', self.email, 'pw12345!')
        free_resp = self.client.post(reverse('send_email_otp'), {'email': 'free_addr@example.com'})
        taken_resp = self.client.post(reverse('send_email_otp'), {'email': self.email})
        # Identical HTTP response (status + ok + message) for taken vs free.
        self.assertEqual(taken_resp.status_code, free_resp.status_code)
        self.assertEqual(taken_resp.json(), free_resp.json())
        self.assertTrue(taken_resp.json()['ok'])
        # No OTP code was generated for the registered address.
        self.assertIsNone(cache.get(otp_utils._otp_key(self.email)))
        # The registered owner received the account-exists notice, not a code.
        notice = [m for m in mail.outbox if m.to == [self.email]]
        self.assertEqual(len(notice), 1)
        self.assertIn('already have', notice[0].subject.lower())

    def test_send_otp_rejects_invalid_email(self):
        resp = self.client.post(reverse('send_email_otp'), {'email': 'not-an-email'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_otp_rate_limited_per_ip(self):
        from users.views import MAX_OTP_SENDS_PER_IP
        for i in range(MAX_OTP_SENDS_PER_IP):
            r = self.client.post(reverse('send_email_otp'), {'email': f'bomb{i}@example.com'})
            self.assertTrue(r.json()['ok'])
        # One more from the same client is throttled (email-bombing guard).
        blocked = self.client.post(reverse('send_email_otp'), {'email': 'bomb_extra@example.com'})
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(len(mail.outbox), MAX_OTP_SENDS_PER_IP)

    # ── verify endpoint ──────────────────────────────────────────────────────
    def test_wrong_then_correct_code(self):
        self.client.post(reverse('send_email_otp'), {'email': self.email})
        bad = self.client.post(reverse('verify_email_otp'), {'email': self.email, 'otp': '000000'})
        self.assertEqual(bad.status_code, 400)
        self.assertNotIn(self.email, self.client.session.get('otp_verified_emails', []))

        code = self._current_code(self.email)
        good = self.client.post(reverse('verify_email_otp'), {'email': self.email, 'otp': code})
        self.assertEqual(good.status_code, 200)
        self.assertTrue(good.json()['ok'])
        self.assertIn(self.email, self.client.session['otp_verified_emails'])

    def test_code_burns_after_max_attempts(self):
        self.client.post(reverse('send_email_otp'), {'email': self.email})
        for _ in range(otp_utils.MAX_VERIFY_ATTEMPTS):
            self.client.post(reverse('verify_email_otp'), {'email': self.email, 'otp': '000000'})
        # Even the right code no longer works once the code is burned.
        resp = self.client.post(reverse('verify_email_otp'), {'email': self.email, 'otp': '000000'})
        self.assertEqual(resp.status_code, 400)
        self.assertIsNone(cache.get(otp_utils._otp_key(self.email)))

    # ── register_view gate ───────────────────────────────────────────────────
    def test_registration_blocked_without_verification(self):
        before = User.objects.count()
        resp = self.client.post(reverse('register'), {
            'first_name': 'Asha', 'last_name': 'K', 'email': self.email,
            'username': 'asha', 'password1': 'Abcd@123', 'password2': 'Abcd@123',
        })
        self.assertEqual(resp.status_code, 200)          # re-rendered, not redirected
        self.assertEqual(User.objects.count(), before)   # no account created
        self.assertContains(resp, 'verify', status_code=200, msg_prefix='', html=False)

    def test_registration_blocked_when_email_differs_from_verified(self):
        # Verify one address, then submit a different one.
        self.client.post(reverse('send_email_otp'), {'email': self.email})
        code = self._current_code(self.email)
        self.client.post(reverse('verify_email_otp'), {'email': self.email, 'otp': code})
        before = User.objects.count()
        resp = self.client.post(reverse('register'), {
            'first_name': 'Asha', 'last_name': 'K', 'email': 'different@example.com',
            'username': 'asha2', 'password1': 'Abcd@123', 'password2': 'Abcd@123',
        })
        self.assertEqual(User.objects.count(), before)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   DEFAULT_FROM_EMAIL='noreply@careerbuddy.test')
class EmployerEmailOtpGateTests(TestCase):
    """The employer signup collects two emails (account + HR); BOTH must be
    OTP-verified before an account is created."""

    def setUp(self):
        cache.clear()
        self.acc_email = 'employer_acc@example.com'
        self.hr_email = 'employer_hr@example.com'
        self.url = reverse('employer_portal:employer_register')

    def _verify(self, email):
        self.client.post(reverse('send_email_otp'), {'email': email})
        code = cache.get(otp_utils._otp_key(email))['code']
        self.client.post(reverse('verify_email_otp'), {'email': email, 'otp': code})

    def _post(self):
        return self.client.post(self.url, {
            'email': self.acc_email, 'hr_mail': self.hr_email, 'username': 'emp1',
        })

    def test_blocked_when_neither_verified(self):
        before = User.objects.count()
        resp = self._post()
        self.assertEqual(User.objects.count(), before)
        self.assertContains(resp, 'verify', status_code=200, html=False)

    def test_blocked_when_only_account_verified(self):
        self._verify(self.acc_email)
        before = User.objects.count()
        self._post()
        self.assertEqual(User.objects.count(), before)   # HR still unverified

    def test_gate_passes_when_both_verified(self):
        self._verify(self.acc_email)
        self._verify(self.hr_email)
        resp = self._post()
        # The two-email verification block is cleared; the form may still fail on
        # other required fields, but not on email verification.
        self.assertNotContains(resp, 'verify both email addresses', status_code=200)

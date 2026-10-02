"""Login must accept either a username or an email address."""
from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class EmailOrUsernameLoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('akhil', 'akhil@example.com', 'pw12345!')

    def test_authenticate_by_username(self):
        self.assertEqual(authenticate(username='akhil', password='pw12345!'), self.user)

    def test_authenticate_by_email(self):
        self.assertEqual(authenticate(username='akhil@example.com', password='pw12345!'), self.user)

    def test_authenticate_by_email_case_insensitive(self):
        self.assertEqual(authenticate(username='AKHIL@Example.com', password='pw12345!'), self.user)

    def test_wrong_password_rejected(self):
        self.assertIsNone(authenticate(username='akhil@example.com', password='wrong'))
        self.assertIsNone(authenticate(username='akhil', password='wrong'))

    def test_unknown_identifier_rejected(self):
        self.assertIsNone(authenticate(username='nobody@example.com', password='pw12345!'))

    def test_login_view_accepts_email(self):
        resp = self.client.post(reverse('login'), {'username': 'akhil@example.com', 'password': 'pw12345!'})
        self.assertEqual(resp.status_code, 302)                 # redirected on success
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_duplicate_email_prefers_most_recent(self):
        # Two accounts share an email (legacy data); email login must stay usable.
        newer = User.objects.create_user('akhil2', 'akhil@example.com', 'pw12345!')
        self.assertEqual(authenticate(username='akhil@example.com', password='pw12345!'), newer)
        # Exact username still resolves to the right account.
        self.assertEqual(authenticate(username='akhil', password='pw12345!'), self.user)

"""Send a one-off test email through the configured SMTP backend.

Usage:
    python manage.py send_test_email you@example.com

Use this after editing EMAIL_* in .env to confirm the ZeptoMail SMTP
credentials, host and port actually work before relying on it for real
signups, applications or payment receipts.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class Command(BaseCommand):
    help = 'Send a test email through the configured SMTP backend to verify it is working.'

    def add_arguments(self, parser):
        parser.add_argument('to_email', type=str, help='Address to send the test email to.')

    def handle(self, *args, **options):
        to_email = options['to_email'].strip()
        try:
            validate_email(to_email)
        except ValidationError:
            raise CommandError(f"'{to_email}' is not a valid email address.")

        self.stdout.write(
            f'Sending test email via {settings.EMAIL_HOST}:{settings.EMAIL_PORT} '
            f'(TLS={settings.EMAIL_USE_TLS}, SSL={settings.EMAIL_USE_SSL}) '
            f'from {settings.DEFAULT_FROM_EMAIL} to {to_email} ...'
        )
        try:
            send_mail(
                subject='Career Buddy — SMTP test email',
                message='This is a test email confirming your SMTP configuration is working.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f'Failed to send test email: {exc}')

        self.stdout.write(self.style.SUCCESS(f'Test email sent successfully to {to_email}.'))

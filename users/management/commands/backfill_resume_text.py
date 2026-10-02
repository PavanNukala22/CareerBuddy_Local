"""
Extracts and stores resume text for every profile that has an uploaded resume
but no extracted text yet, so existing candidates become searchable by the
actual skills / experience / location in their resume.

Usage:
    python manage.py backfill_resume_text
    python manage.py backfill_resume_text --all   # re-extract even if text exists
"""

from django.core.management.base import BaseCommand

from users.models import UserProfile


class Command(BaseCommand):
    help = "Extract and store resume text for candidates who have an uploaded resume."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true",
            help="Re-extract for every profile with a resume (not just empty ones).",
        )

    def handle(self, *args, **options):
        qs = UserProfile.objects.exclude(resume='').exclude(resume__isnull=True)
        if not options["all"]:
            qs = qs.filter(resume_text='')

        total = qs.count()
        done = 0
        skipped = 0
        for p in qs:
            before = p.resume_text or ''
            p.update_resume_text()
            if (p.resume_text or '') and p.resume_text != before:
                done += 1
                self.stdout.write(f"  ✓ {p.user.username} ({len(p.resume_text)} chars)")
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Processed {total} profile(s): extracted {done}, skipped {skipped}."
        ))

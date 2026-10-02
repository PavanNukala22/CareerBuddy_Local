"""
Imports the interview question bank from data/interview_questions.csv into the
FAQQuestion table.

This populates the resume mock-interview question bank on a fresh database, so a
deployment does not need a copy of the developer's database.

CSV columns expected: topic, difficulty, question_text

Usage:
    python manage.py import_interview_questions
    python manage.py import_interview_questions --path custom/path.csv
"""

import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from career_app.models import FAQQuestion


class Command(BaseCommand):
    help = "Load interview questions from data/interview_questions.csv into FAQQuestion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=None,
            help="Path to the CSV file (defaults to <BASE_DIR>/data/interview_questions.csv).",
        )

    def handle(self, *args, **options):
        csv_path = options["path"] or os.path.join(
            str(settings.BASE_DIR), "data", "interview_questions.csv"
        )

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f"CSV not found: {csv_path}"))
            return

        to_create = []
        skipped = 0
        with open(csv_path, encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic = (row.get("topic") or "").strip().lower()
                question_text = (row.get("question_text") or "").strip()
                difficulty = (row.get("difficulty") or "").strip() or None

                if not topic or not question_text:
                    skipped += 1
                    continue

                to_create.append(
                    FAQQuestion(
                        topic=topic,
                        question_text=question_text[:500],
                        difficulty=difficulty,
                    )
                )

        if not to_create:
            self.stderr.write(self.style.WARNING("No valid rows found in CSV."))
            return

        before = FAQQuestion.objects.count()
        # ignore_conflicts respects the (topic, question_text) unique constraint,
        # so re-running is safe and only inserts new questions.
        FAQQuestion.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=1000)
        after = FAQQuestion.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f"Imported {after - before} new question(s) "
            f"({skipped} row(s) skipped, {after} total in DB)."
        ))

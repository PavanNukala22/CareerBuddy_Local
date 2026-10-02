"""
Imports FAQ/interview question banks from CSV folders into the FAQQuestion table.

Handles both CSV layouts used in this project:
  * data/interview_questions.csv      -> topic, difficulty, question_text
  * Interview_data/*.csv              -> Topic, Subtopic, Question

Header matching is case-insensitive, so either style loads without conversion.
Rows without a difficulty are stored with difficulty=NULL; the interview
question picker treats those as usable at any experience level.

It also seeds the behavioural and experience banks (topics "behavioural" and
"experience") so the mock interview can be assembled entirely from the DB with
no LLM call.

Usage:
    python manage.py import_question_bank                  # data/ + Interview_data/
    python manage.py import_question_bank --dir Interview_data
    python manage.py import_question_bank --path some/file.csv
    python manage.py import_question_bank --no-banks       # skip behavioural/experience seed
"""

import csv
import glob
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count

from career_app.models import FAQQuestion

# Accepted column names -> model field
TOPIC_KEYS = ("topic",)
QUESTION_KEYS = ("question_text", "question")
DIFFICULTY_KEYS = ("difficulty", "level")

DEFAULT_DIRS = ("data", "Interview_data")


def _pick(row_lower, keys):
    """Return the first non-empty value among `keys` from a lower-cased row dict."""
    for key in keys:
        value = (row_lower.get(key) or "").strip()
        if value:
            return value
    return ""


class Command(BaseCommand):
    help = "Load question bank CSVs (data/, Interview_data/) into FAQQuestion."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=None, help="Import a single CSV file.")
        parser.add_argument("--dir", default=None, help="Import every *.csv in this folder.")
        parser.add_argument(
            "--no-banks", action="store_true",
            help="Do not seed the behavioural/experience question banks.",
        )

    def handle(self, *args, **options):
        base = str(settings.BASE_DIR)

        if options["path"]:
            files = [options["path"]]
        elif options["dir"]:
            files = sorted(glob.glob(os.path.join(base, options["dir"], "*.csv")))
        else:
            files = []
            for folder in DEFAULT_DIRS:
                files.extend(sorted(glob.glob(os.path.join(base, folder, "*.csv"))))

        if not files and options["no_banks"]:
            self.stderr.write(self.style.ERROR("No CSV files found."))
            return

        before = FAQQuestion.objects.count()
        total_skipped = 0

        for path in files:
            if not os.path.exists(path):
                self.stderr.write(self.style.ERROR(f"CSV not found: {path}"))
                continue
            created, skipped = self._import_csv(path)
            total_skipped += skipped
            self.stdout.write(
                f"  {os.path.relpath(path, base)}: +{created} new, {skipped} skipped"
            )

        if not options["no_banks"]:
            seeded = self._seed_banks()
            self.stdout.write(f"  behavioural/experience banks: +{seeded} new")

        after = FAQQuestion.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Imported {after - before} new question(s); "
            f"{total_skipped} row(s) skipped; {after} total in FAQQuestion."
        ))

        self.stdout.write("\nTopics now in the bank:")
        rows = FAQQuestion.objects.values("topic").annotate(n=Count("id")).order_by("-n")
        for row in rows[:30]:
            self.stdout.write(f"  {row['n']:>6}  {row['topic']}")
        if len(rows) > 30:
            self.stdout.write(f"  ... and {len(rows) - 30} more topic(s)")

    def _import_csv(self, path):
        to_create = []
        skipped = 0
        # utf-8-sig strips the BOM Excel adds; errors=ignore matches the older importer.
        with open(path, encoding="utf-8-sig", errors="ignore", newline="") as f:
            for row in csv.DictReader(f):
                row_lower = {(k or "").strip().lower(): v for k, v in row.items()}
                topic = _pick(row_lower, TOPIC_KEYS).lower()
                question = _pick(row_lower, QUESTION_KEYS)
                difficulty = _pick(row_lower, DIFFICULTY_KEYS) or None

                if not topic or not question:
                    skipped += 1
                    continue

                to_create.append(FAQQuestion(
                    topic=topic[:100],
                    question_text=question[:500],
                    difficulty=difficulty,
                ))

        return self._bulk_insert(to_create), skipped

    def _seed_banks(self):
        """Store the hard-coded behavioural/experience/academic banks as DB rows."""
        from career_app.resume_utils import (
            BEHAVIOURAL_QUESTIONS, EXPERIENCE_QUESTIONS, ACADEMIC_PROJECT_QUESTIONS,
        )

        to_create = [
            FAQQuestion(topic="behavioural", question_text=q[:500], difficulty="Easy")
            for q in BEHAVIOURAL_QUESTIONS
        ] + [
            FAQQuestion(topic="experience", question_text=q[:500], difficulty="Easy")
            for q in EXPERIENCE_QUESTIONS
        ] + [
            FAQQuestion(topic="academic_project", question_text=q[:500], difficulty="Easy")
            for q in ACADEMIC_PROJECT_QUESTIONS
        ]
        return self._bulk_insert(to_create)

    def _bulk_insert(self, objs):
        if not objs:
            return 0
        before = FAQQuestion.objects.count()
        # ignore_conflicts respects the (topic, question_text) unique constraint,
        # so re-running the import only ever adds genuinely new questions.
        FAQQuestion.objects.bulk_create(objs, ignore_conflicts=True, batch_size=1000)
        return FAQQuestion.objects.count() - before

"""Backfill industry on domain FAQQuestion rows that predate the industry column.

The original CSV imports (interview_questions.csv, the older question bank) had
no industry column, so their rows have industry=''. Domain-question selection
is now gated by industry, and blank-industry rows are excluded whenever a resume
matches any industry — which silently dropped the whole legacy tech bank
(python, java, docker, kubernetes, …) for IT candidates, leaving only the
newer xlsx AWS topics. Tag those rows so the gate treats them like every other:

  * staffing/workforce service topics -> "workforce outsourcing & managed staffing"
  * everything else (the tech bank)    -> "it & software"

Behavioural / experience / academic banks are left untouched (BANK_TOPICS).
"""
import re

from django.db import migrations

BANK_TOPICS = ('behavioural', 'experience', 'academic_project')
IT_INDUSTRY = 'it & software'
STAFFING_INDUSTRY = 'workforce outsourcing & managed staffing'
_STAFFING_RE = re.compile(
    r'workforce|staffing|recruitment|outsourcing|payroll|hrms|mobility|'
    r'turnaround|leadership hiring|skill development|plant operations|'
    r'\brpo\b|process outsourcing|executive search'
)


def backfill(apps, schema_editor):
    FAQQuestion = apps.get_model('career_app', 'FAQQuestion')
    blank = FAQQuestion.objects.filter(industry='').exclude(topic__in=BANK_TOPICS)
    topics = sorted(set(blank.values_list('topic', flat=True)))
    for topic in topics:
        industry = STAFFING_INDUSTRY if _STAFFING_RE.search(topic or '') else IT_INDUSTRY
        FAQQuestion.objects.filter(industry='', topic=topic).update(industry=industry)


def noop(apps, schema_editor):
    # Non-reversible in a meaningful way; leave the tags in place on rollback.
    pass


class Migration(migrations.Migration):
    dependencies = [('career_app', '0014_faqquestion_industry')]
    operations = [migrations.RunPython(backfill, noop)]

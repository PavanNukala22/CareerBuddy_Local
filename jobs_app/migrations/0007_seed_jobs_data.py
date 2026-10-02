"""
Data migration: seed the job postings into the database.

This makes the curated job dataset PERMANENT and reproducible: any developer who
clones the repo and runs `python manage.py migrate` will get all the jobs, with
no separate seeding step required.

It reuses the same SEEDED_JOBS data as the `seed_jobs` management command and is
idempotent (get_or_create), so it is safe alongside that command and safe to
re-run conceptually (migrations only apply once per database anyway).
"""

from django.db import migrations


def _company_username(company_name):
    # Mirror the exact username logic used by the seed_jobs command so both
    # create/reuse the SAME employer users (no duplicates).
    return 'seed_' + company_name.lower().replace(' ', '_').replace('-', '_').replace('&', 'and')[:40]


def seed_jobs_forward(apps, schema_editor):
    # Lazy import of the data list only (no ORM at import time)
    from jobs_app.management.commands.seed_jobs import SEEDED_JOBS

    User = apps.get_model('auth', 'User')
    EmployerProfile = apps.get_model('jobs_app', 'EmployerProfile')
    JobPosting = apps.get_model('jobs_app', 'JobPosting')

    employer_cache = {}

    for job_data in SEEDED_JOBS:
        (
            company_name, industry, emp_location,
            title, description, requirements,
            skills, job_type, experience,
            salary_min, salary_max, openings,
        ) = job_data

        if company_name not in employer_cache:
            company_username = _company_username(company_name)
            company_user, _created = User.objects.get_or_create(
                username=company_username,
                defaults={
                    'email': f'{company_username}@seeded.com',
                    'first_name': company_name[:30],
                    'is_active': False,
                    'password': '!',  # unusable password
                },
            )
            employer, _emp_created = EmployerProfile.objects.get_or_create(
                user=company_user,
                defaults={
                    'company_name': company_name,
                    'industry': industry,
                    'location': emp_location,
                    'company_size': '500+',
                    'description': f'Seeded employer profile for {company_name}.',
                    'company_website': '',
                },
            )
            employer_cache[company_name] = employer
        else:
            employer = employer_cache[company_name]

        JobPosting.objects.get_or_create(
            title=title,
            employer=employer,
            defaults={
                'description': description.strip(),
                'requirements': requirements.strip(),
                'skills_required': skills,
                'job_type': job_type,
                'experience': experience,
                'salary_min': salary_min,
                'salary_max': salary_max,
                'location': emp_location,
                'openings': openings,
                'status': 'active',
                'is_seeded': True,
            },
        )


def seed_jobs_reverse(apps, schema_editor):
    # No-op on reverse: never auto-delete job data on migrate rollback.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('jobs_app', '0006_add_notice_period_other_field'),
    ]

    operations = [
        migrations.RunPython(seed_jobs_forward, seed_jobs_reverse),
    ]

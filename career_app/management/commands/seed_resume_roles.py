"""Copy the built-in Resume Builder roles into the admin-editable table.

    python manage.py seed_resume_roles              # add missing roles only
    python manage.py seed_resume_roles --overwrite  # reset existing rows to the defaults

Seeding is optional: the builder works from the built-in data without it. It
only exists so admins can edit a role's content in the Django admin.
"""
from django.core.management.base import BaseCommand

from career_app.models import ResumeRoleTemplate
from career_app.resume_roles import BUILTIN_ROLES, summary_templates


class Command(BaseCommand):
    help = 'Copy the built-in Resume Builder roles into ResumeRoleTemplate for editing in the admin.'

    def add_arguments(self, parser):
        parser.add_argument('--overwrite', action='store_true',
                            help='Reset rows that already exist to the built-in values.')

    def handle(self, *args, overwrite=False, **options):
        created = updated = skipped = 0
        for position, role in enumerate(BUILTIN_ROLES, start=1):
            values = {
                'title': role['title'],
                'category': role['category'],
                'industry': role['industry'],
                'icon': role['icon'],
                'subtitle': role['subtitle'],
                'description': role['description'],
                'responsibilities': '\n'.join(role['responsibilities']),
                'required_skills': '\n'.join(role['required_skills']),
                'recommended_skills': '\n'.join(role['recommended_skills']),
                'career_path': '\n'.join(role['career_path']),
                'certifications': '\n'.join(role['certifications']),
                'experience_label': role['experience_label'],
                'role_fields': [{'label': f['label'], 'options': f['options']} for f in role['fields']],
                'level_suggestions': role['levels'],
                'summary_templates': summary_templates(role),
                'display_order': position * 10,
            }
            row = ResumeRoleTemplate.objects.filter(slug=role['slug']).first()
            if row is None:
                ResumeRoleTemplate.objects.create(slug=role['slug'], **values)
                created += 1
            elif overwrite:
                for key, value in values.items():
                    setattr(row, key, value)
                row.save()
                updated += 1
            else:
                skipped += 1
        self.stdout.write(self.style.SUCCESS(
            f'Resume roles: {created} created, {updated} updated, {skipped} left unchanged.'))

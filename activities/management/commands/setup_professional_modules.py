from django.core.management.base import BaseCommand
from django.db import transaction

from activities.models import Activity, SubActivity, Exercise


# The four professional AI learning modules.
#
# Orders 1–20 belong to the Business English activities (populate_activities) and
# 25–27 to the Interactive Workshops, so these occupy 21–24. Professional
# Speaking is pinned to order 24 because it is the Free Plan gateway activity
# (see FREE_PLAN_ACTIVITY_ORDERS in activities/views.py).
#
# Each module is keyed on its (unique) title, so this command is fully
# idempotent: re-running it updates the existing rows in place instead of
# shifting every activity's order and duplicating modules.
MODULES = [
    {
        'order': 21,
        'title': 'Professional Passage Writing',
        'category': 'writing',
        'level': 'Intermediate to Advanced',
        'duration': '45 mins',
        'materials': 'Keyboard, writing prompts',
        'objective': 'Improve professional writing skills with real-time AI feedback on grammar, tone, and structure.',
        'icon_class': 'fas fa-pen',
        'color_class': 'success',
    },
    {
        'order': 22,
        'title': 'Listen & Learn',
        'category': 'listening',
        'level': 'Intermediate',
        'duration': '30-45 min',
        'materials': 'Headphones, quiet environment',
        'objective': 'Enhance listening comprehension and transcription accuracy with AI-powered feedback.',
        'icon_class': 'fas fa-headphones',
        'color_class': 'info',
    },
    {
        'order': 23,
        'title': 'Professional Reading',
        'category': 'reading',
        'level': 'Beginner',
        'duration': '20-30 min',
        'materials': 'Reading passages, quiet room',
        'objective': 'Practice reading aloud and improve pronunciation and pace with AI analysis.',
        'icon_class': 'fas fa-book-open',
        'color_class': 'warning',
    },
    {
        'order': 24,
        'title': 'Professional Speaking',
        'category': 'speaking',
        'level': 'Intermediate to Advanced',
        'duration': '60-90 min',
        'materials': 'Microphone, quiet room, notebook',
        'objective': 'Master professional fluency and pronunciation through AI-driven speaking practice.',
        'icon_class': 'fas fa-microphone',
        'color_class': 'primary',
    },
]


class Command(BaseCommand):
    help = (
        'Idempotently set up the four professional AI learning modules '
        '(orders 21-24). Safe to re-run: it updates existing modules in place '
        'and never shifts other activities or duplicates modules.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-only',
            action='store_true',
            help='Only create missing modules; leave existing ones untouched. '
                 'populate_activities passes this on its default (safe fill) run.',
        )

    def handle(self, *args, **options):
        create_only = options.get('create_only', False)
        with transaction.atomic():
            for m_data in MODULES:
                order = m_data['order']

                if create_only and Activity.objects.filter(title=m_data['title']).exists():
                    self.stdout.write(f"Skipped (exists): {m_data['title']}")
                    continue

                # Guard against a pre-existing corruption where a *different*
                # activity already sits on this module's target order (e.g. from
                # older buggy runs that shifted orders). Keying on the unique
                # title, we would otherwise hit an IntegrityError on order.
                clash = Activity.objects.filter(order=order).exclude(title=m_data['title']).first()
                if clash:
                    self.stdout.write(self.style.ERROR(
                        f"Order {order} is occupied by '{clash.title}'. "
                        f"Skipping '{m_data['title']}' to avoid clobbering it. "
                        f"Resolve the order conflict, then re-run."
                    ))
                    continue

                activity, created = Activity.objects.update_or_create(
                    title=m_data['title'],
                    defaults=m_data,
                )
                verb = 'Created' if created else 'Updated'
                self.stdout.write(f'{verb} activity: {activity.order} - {activity.title}')

                # A placeholder sub-activity/exercise so the module renders in the
                # standard UI. get_or_create keeps this non-destructive on re-run.
                sub, _ = SubActivity.objects.get_or_create(
                    activity=activity,
                    order=1,
                    defaults={
                        'title': 'AI-Powered Practice',
                        'description': f'Complete the {activity.title} exercise using AI-driven feedback.',
                        'instructions': f'Follow the on-screen AI prompts to complete your {activity.category} practice session.',
                    },
                )

                Exercise.objects.get_or_create(
                    sub_activity=sub,
                    order=1,
                    defaults={
                        'title': f'{activity.title} Module',
                        'exercise_type': 'writing',  # placeholder
                        'instructions': f'Start your {activity.category} practice session.',
                    },
                )

        self.stdout.write(self.style.SUCCESS('Professional modules setup complete!'))

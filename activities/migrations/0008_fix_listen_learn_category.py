"""
Data fix: make the chatbot's "open Listen & Learn" land on the activity.

The chatbot routes Listen & Learn to /activities/?category=listening, and
activity_list() redirects straight to the activity when exactly one active
Activity has category='listening'. Databases set up before that change hold
Listen & Learn under a different category (and at a different order number,
e.g. 26 instead of 22), so the page showed "No activities found".

This migration:
  * sets category='listening' and is_active=True on the existing
    Listen & Learn row, leaving its id, order and user progress untouched;
  * creates the row only if it is missing, at the next free order number,
    so it never clashes with another activity (e.g. JAM at order 22).

Safe to run on any database, any number of times.
"""
from django.db import migrations

TITLE_REGEX = r'^\s*listen\s*(&|and)\s*learn\s*$'


def fix_listen_learn(apps, schema_editor):
    Activity = apps.get_model('activities', 'Activity')
    SubActivity = apps.get_model('activities', 'SubActivity')
    Exercise = apps.get_model('activities', 'Exercise')

    rows = Activity.objects.filter(title__iregex=TITLE_REGEX)

    if rows.exists():
        rows.update(category='listening', is_active=True)
        return

    # A brand-new database has no activities yet: there is nothing to fix,
    # and the seeding commands create Listen & Learn at its proper order (22).
    # Creating it here took order 1, so populate_activities saw order 1 as
    # "already existed" and Elevator Pitch Workshop was never created (26
    # activities instead of 27 on every fresh install and test run).
    if not Activity.objects.exists():
        return

    last =Activity.objects.order_by('-order').values_list('order', flat=True).first() or 0
    activity = Activity.objects.create(
        order=last + 1,
        title='Listen & Learn',
        category='listening',
        level='Intermediate',
        duration='30-45 min',
        materials='Headphones, quiet environment',
        objective='Enhance listening comprehension and transcription accuracy with AI-powered feedback.',
        icon_class='fas fa-headphones',
        color_class='info',
        is_active=True,
    )
    sub = SubActivity.objects.create(
        activity=activity,
        order=1,
        title='AI-Powered Practice',
        description='Complete the Listen & Learn exercise using AI-driven feedback.',
        instructions='Follow the on-screen AI prompts to complete your listening practice session.',
    )
    Exercise.objects.create(
        sub_activity=sub,
        order=1,
        title='Listen & Learn Module',
        exercise_type='writing',  # placeholder, same as setup_professional_modules
        instructions='Start your listening practice session.',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('activities', '0007_bingo_instructions_with_win'),
    ]

    operations = [
        migrations.RunPython(fix_listen_learn, migrations.RunPython.noop),
    ]

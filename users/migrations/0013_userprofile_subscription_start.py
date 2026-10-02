from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_userprofile_additional_educations_json'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='subscription_start',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When the current paid plan was activated',
            ),
        ),
    ]

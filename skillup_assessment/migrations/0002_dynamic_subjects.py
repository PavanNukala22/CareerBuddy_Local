# Generalizes Certificate from a fixed 3-module system to the ~27 dynamic
# subjects in skillup_assessment.subjects.SUBJECTS, and adds QuizAttempt --
# the real, server-persisted quiz history that eligibility is now derived
# from (spec section 17: backend must be the source of truth, not
# localStorage/frontend state).
import django.db.models.deletion
import skillup_assessment.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('skillup_assessment', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='certificate',
            name='one_certificate_per_user_per_module',
        ),
        migrations.RenameField(
            model_name='certificate',
            old_name='module',
            new_name='subject',
        ),
        migrations.AlterField(
            model_name='certificate',
            name='subject',
            field=models.CharField(db_index=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='certificate',
            name='pdf_file',
            field=models.FileField(blank=True, null=True, upload_to=skillup_assessment.models.certificate_pdf_path),
        ),
        migrations.AddConstraint(
            model_name='certificate',
            constraint=models.UniqueConstraint(fields=('user', 'subject'), name='one_certificate_per_user_per_subject'),
        ),
        migrations.CreateModel(
            name='QuizAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(db_index=True, max_length=32)),
                ('score', models.PositiveIntegerField()),
                ('total', models.PositiveIntegerField()),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quiz_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.AddIndex(
            model_name='quizattempt',
            index=models.Index(fields=['user', 'subject'], name='skillup_ass_user_id_52fc36_idx'),
        ),
    ]

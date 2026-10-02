from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Topic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('difficulty', models.CharField(choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], default='medium', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['title']},
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bio', models.TextField(blank=True)),
                ('avatar_initial', models.CharField(blank=True, max_length=2)),
                ('total_sessions', models.IntegerField(default=0)),
                ('total_minutes', models.IntegerField(default=0)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='jam_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='JAMSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('audio_file', models.FileField(blank=True, null=True, upload_to='audio/')),
                ('duration', models.IntegerField(default=0, help_text='Duration in seconds')),
                ('confidence_score', models.IntegerField(blank=True, choices=[(1, '⭐ Nervous'), (2, '⭐⭐ Unsure'), (3, '⭐⭐⭐ Okay'), (4, '⭐⭐⭐⭐ Confident'), (5, '⭐⭐⭐⭐⭐ Great!')], null=True)),
                ('fluency_score', models.IntegerField(blank=True, choices=[(1, '⭐ Many pauses'), (2, '⭐⭐ Some pauses'), (3, '⭐⭐⭐ Moderate'), (4, '⭐⭐⭐⭐ Mostly fluent'), (5, '⭐⭐⭐⭐⭐ Very fluent')], null=True)),
                ('language_score', models.IntegerField(blank=True, choices=[(1, '⭐ Basic'), (2, '⭐⭐ Limited'), (3, '⭐⭐⭐ Adequate'), (4, '⭐⭐⭐⭐ Good'), (5, '⭐⭐⭐⭐⭐ Excellent')], null=True)),
                ('pronunciation_score', models.IntegerField(blank=True, choices=[(1, '⭐ Unclear'), (2, '⭐⭐ Needs work'), (3, '⭐⭐⭐ Acceptable'), (4, '⭐⭐⭐⭐ Clear'), (5, '⭐⭐⭐⭐⭐ Native-like')], null=True)),
                ('time_management_score', models.IntegerField(blank=True, choices=[(1, '⭐ Very short'), (2, '⭐⭐ Too brief'), (3, '⭐⭐⭐ Moderate'), (4, '⭐⭐⭐⭐ Good use'), (5, '⭐⭐⭐⭐⭐ Perfect')], null=True)),
                ('notes', models.TextField(blank=True, help_text='Personal notes about the session')),
                ('transcript', models.TextField(blank=True, help_text='Transcribed text from the session')),
                ('ai_feedback', models.TextField(blank=True, help_text='AI-generated feedback')),
                ('improvement_tips', models.TextField(blank=True, help_text='Actionable improvement roadmap')),
                ('completed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to=settings.AUTH_USER_MODEL)),
                ('topic', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sessions', to='jam_app.topic')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AssessmentGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('final_report', models.TextField(blank=True)),
                ('completed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('easy_session', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assessment_easy', to='jam_app.jamsession')),
                ('hard_session', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assessment_hard', to='jam_app.jamsession')),
                ('medium_session', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assessment_medium', to='jam_app.jamsession')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assessments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
    ]

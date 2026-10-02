from django.db import migrations

TOPICS = [
    # Easy
    ("My Favorite Food", "Talk about your favorite dish, why you love it, and any memories associated with it.", "easy"),
    ("My Best Friend", "Describe your best friend, how you met, and what makes them special.", "easy"),
    ("A Memorable Day", "Share a day that stands out in your memory and why it was significant.", "easy"),
    ("My Morning Routine", "Walk through what you typically do every morning from waking up.", "easy"),
    ("Technology in Daily Life", "Discuss how technology has changed your everyday activities.", "easy"),
    ("My Favorite Hobby", "Talk about a hobby you enjoy and what you get out of it.", "easy"),

    # Medium
    ("Importance of Education", "Discuss why education matters and how it shapes a person's future.", "medium"),
    ("Social Media: Boon or Bane?", "Explore both positive and negative effects of social media on society.", "medium"),
    ("Climate Change Challenges", "Talk about the challenges posed by climate change and possible solutions.", "medium"),
    ("Work-Life Balance", "Discuss the importance of balancing professional and personal life.", "medium"),
    ("Leadership Qualities", "What makes a great leader? Share your thoughts with examples.", "medium"),
    ("The Future of Work", "How do you see the workplace evolving in the next 10 years?", "medium"),
    ("Health and Wellness", "Why is maintaining good health essential in today's fast-paced world?", "medium"),
    ("Travelling Experiences", "How does travel broaden one's perspective on life?", "medium"),

    # Hard
    ("Artificial Intelligence: Promise and Peril", "Critically analyze the opportunities and risks of advanced AI systems.", "hard"),
    ("Democracy in the Digital Age", "How has digitalization impacted democratic processes globally?", "hard"),
    ("Economic Inequality", "Explore causes, consequences, and solutions to growing economic inequality.", "hard"),
    ("Mental Health Stigma", "Why does stigma around mental health persist and how can we address it?", "hard"),
    ("Globalization vs. Cultural Identity", "How do we balance global interconnectedness with preserving cultural heritage?", "hard"),
    ("Ethics in Science", "Where should the moral boundaries of scientific research lie?", "hard"),
]


def add_topics(apps, schema_editor):
    Topic = apps.get_model('jam_app', 'Topic')
    for title, description, difficulty in TOPICS:
        Topic.objects.get_or_create(
            title=title,
            defaults={'description': description, 'difficulty': difficulty, 'is_active': True}
        )


def remove_topics(apps, schema_editor):
    Topic = apps.get_model('jam_app', 'Topic')
    Topic.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('jam_app', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_topics, remove_topics),
    ]

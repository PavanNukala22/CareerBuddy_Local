"""
Seeds realistic REGISTERED STUDENT candidates (User + UserProfile) into the DB
so the employer Candidate Search returns real, well-skilled candidates.

Every candidate stores full profile information — skills, experience, location,
industry, education, contact — exactly as a real student registration would, so
they are retrievable by the employer's skill-based candidate search.

Covers both IT and non-IT domains so searches like "python", "java", "sales",
"customer support", "accounting", "civil" all return matching candidates.

Usage:
    python manage.py seed_candidates
    python manage.py seed_candidates --clear   # remove previously seeded candidates first
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from users.models import UserProfile

# Seeded candidate usernames share this prefix so --clear only removes seeded ones.
SEED_PREFIX = "cand_"

DEFAULT_PASSWORD = "Candidate@123"

CANDIDATES = [
    # ── IT / Software ──────────────────────────────────────────────────────
    {"first": "Rohan", "last": "Deshmukh", "email": "rohan.deshmukh@example.com", "mobile": "9811100001",
     "skills": "Python, Django, REST API, PostgreSQL, Docker, AWS, Git", "exp": 6,
     "location": "Pune, Maharashtra", "industry": "it_software", "degree": "B.Tech (CSE)"},
    {"first": "Sneha", "last": "Kulkarni", "email": "sneha.kulkarni@example.com", "mobile": "9811100002",
     "skills": "Python, Django, Pandas, NumPy, MySQL, Git", "exp": 4,
     "location": "Bengaluru, Karnataka", "industry": "it_software", "degree": "MCA"},
    {"first": "Arjun", "last": "Pillai", "email": "arjun.pillai@example.com", "mobile": "9811100003",
     "skills": "Python, JavaScript, React, Node.js, MongoDB, Git", "exp": 3,
     "location": "Hyderabad, Telangana", "industry": "it_software", "degree": "B.Tech (IT)"},
    {"first": "Vikram", "last": "Iyer", "email": "vikram.iyer@example.com", "mobile": "9811100004",
     "skills": "Java, Spring Boot, Hibernate, Microservices, Kafka, MySQL, Docker", "exp": 7,
     "location": "Chennai, Tamil Nadu", "industry": "it_software", "degree": "B.E (CSE)"},
    {"first": "Pooja", "last": "Nair", "email": "pooja.nair@example.com", "mobile": "9811100005",
     "skills": "Java, Spring, JPA, REST API, Oracle, Maven", "exp": 4,
     "location": "Kochi, Kerala", "industry": "it_software", "degree": "B.Tech (CSE)"},
    {"first": "Aditya", "last": "Rao", "email": "aditya.rao@example.com", "mobile": "9811100006",
     "skills": "React, JavaScript, TypeScript, Redux, Next.js, HTML/CSS, Tailwind", "exp": 5,
     "location": "Bengaluru, Karnataka", "industry": "it_software", "degree": "B.Tech (CSE)"},
    {"first": "Karan", "last": "Malhotra", "email": "karan.malhotra@example.com", "mobile": "9811100007",
     "skills": "Python, Machine Learning, Data Science, TensorFlow, Pandas, SQL, Power BI", "exp": 6,
     "location": "Gurugram, Haryana", "industry": "it_software", "degree": "M.Tech (Data Science)"},
    {"first": "Ananya", "last": "Verma", "email": "ananya.verma@example.com", "mobile": "9811100008",
     "skills": "SQL, PostgreSQL, MySQL, Python, ETL, Airflow, Power BI", "exp": 4,
     "location": "Mumbai, Maharashtra", "industry": "it_software", "degree": "B.Sc (Statistics)"},
    {"first": "Rahul", "last": "Saxena", "email": "rahul.saxena@example.com", "mobile": "9811100009",
     "skills": "AWS, Docker, Kubernetes, Terraform, Jenkins, Linux, Python, CI/CD", "exp": 5,
     "location": "Pune, Maharashtra", "industry": "it_software", "degree": "B.E (IT)"},
    {"first": "Meera", "last": "Joshi", "email": "meera.joshi@example.com", "mobile": "9811100010",
     "skills": "Python, Machine Learning, Deep Learning, PyTorch, NLP, SQL", "exp": 4,
     "location": "Ahmedabad, Gujarat", "industry": "it_software", "degree": "M.Sc (CS)"},
    {"first": "Sanjana", "last": "Reddy", "email": "sanjana.reddy@example.com", "mobile": "9811100011",
     "skills": "Selenium, Testing, Java, TestNG, JIRA, Postman, API Testing", "exp": 3,
     "location": "Hyderabad, Telangana", "industry": "it_software", "degree": "B.Tech (ECE)"},

    # ── Non-IT domains ─────────────────────────────────────────────────────
    {"first": "Suresh", "last": "Babu", "email": "suresh.babu@example.com", "mobile": "9822200001",
     "skills": "Sales, Business Development, Lead Generation, CRM, Negotiation, Communication", "exp": 5,
     "location": "Chennai, Tamil Nadu", "industry": "retail", "degree": "MBA (Marketing)"},
    {"first": "Divya", "last": "Krishnan", "email": "divya.krishnan@example.com", "mobile": "9822200002",
     "skills": "Customer Support, Communication, Email Support, Chat Support, CRM, BPO", "exp": 3,
     "location": "Bengaluru, Karnataka", "industry": "it_software", "degree": "B.Com"},
    {"first": "Ramesh", "last": "Gupta", "email": "ramesh.gupta@example.com", "mobile": "9822200003",
     "skills": "Accounting, Tally, GST, Financial Reporting, Auditing, MS Excel, Taxation", "exp": 6,
     "location": "Delhi", "industry": "finance", "degree": "B.Com, CA (Inter)"},
    {"first": "Priya", "last": "Sharma", "email": "priya.sharma@example.com", "mobile": "9822200004",
     "skills": "Digital Marketing, SEO, Google Ads, Social Media, Content Writing, Analytics", "exp": 4,
     "location": "Mumbai, Maharashtra", "industry": "media", "degree": "BBA"},
    {"first": "Manoj", "last": "Patel", "email": "manoj.patel@example.com", "mobile": "9822200005",
     "skills": "AutoCAD, Civil Engineering, Structural Design, Project Management, Estimation", "exp": 7,
     "location": "Surat, Gujarat", "industry": "construction", "degree": "B.E (Civil)"},
    {"first": "Kavya", "last": "Menon", "email": "kavya.menon@example.com", "mobile": "9822200006",
     "skills": "Nursing, Patient Care, Clinical, First Aid, Medication Administration", "exp": 5,
     "location": "Kochi, Kerala", "industry": "healthcare", "degree": "B.Sc (Nursing)"},
    {"first": "Deepak", "last": "Yadav", "email": "deepak.yadav@example.com", "mobile": "9822200007",
     "skills": "Mechanical Engineering, AutoCAD, SolidWorks, Manufacturing, Quality Control, GD&T", "exp": 6,
     "location": "Coimbatore, Tamil Nadu", "industry": "manufacturing", "degree": "B.E (Mechanical)"},
    {"first": "Neha", "last": "Agarwal", "email": "neha.agarwal@example.com", "mobile": "9822200008",
     "skills": "HR, Recruitment, Payroll, Employee Engagement, Onboarding, HRMS, Communication", "exp": 4,
     "location": "Noida, Uttar Pradesh", "industry": "it_software", "degree": "MBA (HR)"},
]


class Command(BaseCommand):
    help = "Seed realistic registered student candidates (with skills) for the employer candidate search."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete previously seeded candidates before creating.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            removed = User.objects.filter(username__startswith=SEED_PREFIX).count()
            User.objects.filter(username__startswith=SEED_PREFIX).delete()
            self.stdout.write(self.style.WARNING(f"Removed {removed} previously seeded candidate(s)."))

        created = 0
        updated = 0
        for i, c in enumerate(CANDIDATES, start=1):
            username = f"{SEED_PREFIX}{i:02d}_{c['first'].lower()}"
            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": c["email"],
                    "first_name": c["first"],
                    "last_name": c["last"],
                    "is_active": True,
                },
            )
            if was_created:
                user.set_password(DEFAULT_PASSWORD)
                user.save()
                created += 1
            else:
                updated += 1

            # Profile is auto-created by the post_save signal
            p = user.profile
            p.role = "student"
            p.skills = c["skills"]
            p.experience_years = c["exp"]
            p.has_experience = c["exp"] > 0
            p.current_location = c["location"]
            p.preferred_location = c["location"]
            p.industry = c["industry"]
            p.higher_education_degree = c["degree"]
            p.mobile = c["mobile"]
            p.save()

            self.stdout.write(f"  + {c['first']} {c['last']:<12} | {c['exp']}y | {c['skills'][:45]}")

        self.stdout.write(self.style.SUCCESS(
            f"Seeded candidates — created {created}, updated {updated} "
            f"(login password for all: {DEFAULT_PASSWORD})"
        ))

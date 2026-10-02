"""
Generates a set of sample candidate resumes (PDF) into MEDIA_ROOT/resumes/.

These resumes are written in the exact layout that
`jobs_app.views.parse_resumes_from_folder` expects:

  Line 1                -> Candidate name
  "<city>" in header    -> used by the location filter
  "X+ years"            -> used by the experience filter
  KEY SKILLS ... WORK EXPERIENCE  -> the block scanned for skills

Each candidate intentionally mentions their primary skill a different number
of times so the relevance ranking (most mentions first) is easy to see.

Usage:
    python manage.py seed_resumes
    python manage.py seed_resumes --clear   # remove previously seeded files first
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
except ImportError:  # pragma: no cover
    canvas = None


# Every generated file starts with this prefix so --clear can find them safely
# without ever touching real uploaded resumes.
SEED_PREFIX = "Sample_"


# ---------------------------------------------------------------------------
# Candidate data. `primary` is repeated across the summary/skills/bullets so the
# total occurrence count differs per candidate -> drives the relevance ranking.
# ---------------------------------------------------------------------------
CANDIDATES = [
    {
        "name": "Rohan Deshmukh", "email": "rohan.deshmukh@gmail.com",
        "phone": "+91-9811122233", "city": "Pune, Maharashtra", "exp": 6,
        "primary": "Python",
        "summary": ("Python backend engineer with 6+ years of experience. Expert in "
                    "Python web frameworks, Python automation and writing clean, "
                    "testable Python code for high-traffic systems."),
        "skills": ["Python", "Django", "Flask", "FastAPI", "PostgreSQL",
                   "Docker", "AWS", "Git"],
        "experience": [
            ("Senior Python Developer", "TechNova Solutions, Pune", "2021 - Present",
             ["Led a team building Python microservices handling 80K+ daily users.",
              "Migrated legacy scripts to modern Python and Django REST APIs.",
              "Built Python automation pipelines reducing manual work by 60%."]),
            ("Python Developer", "WebCraft Labs, Mumbai", "2018 - 2021",
             ["Developed Python data-processing jobs with Pandas and Celery.",
              "Wrote Python unit tests achieving 90% coverage."]),
        ],
    },
    {
        "name": "Sneha Kulkarni", "email": "sneha.kulkarni@gmail.com",
        "phone": "+91-9822233344", "city": "Bengaluru, Karnataka", "exp": 4,
        "primary": "Python",
        "summary": ("Python developer with 4+ years building data-driven applications "
                    "in Python and Django."),
        "skills": ["Python", "Django", "Pandas", "NumPy", "MySQL", "Redis", "Git"],
        "experience": [
            ("Python Developer", "DataBridge Analytics, Bengaluru", "2020 - Present",
             ["Built Python ETL pipelines for analytics dashboards.",
              "Optimized Python query layers improving response time by 35%."]),
            ("Junior Developer", "InfoEdge, Bengaluru", "2019 - 2020",
             ["Maintained internal Python tooling and reports."]),
        ],
    },
    {
        "name": "Arjun Pillai", "email": "arjun.pillai@gmail.com",
        "phone": "+91-9833344455", "city": "Hyderabad, Telangana", "exp": 3,
        "primary": "Python",
        "summary": "Software engineer with 3+ years of experience, comfortable with Python.",
        "skills": ["Python", "JavaScript", "React", "Node.js", "MongoDB", "Git"],
        "experience": [
            ("Full Stack Developer", "Brightwave Tech, Hyderabad", "2021 - Present",
             ["Built web apps with a Python backend and React frontend.",
              "Integrated third-party APIs and payment gateways."]),
        ],
    },
    {
        "name": "Vikram Iyer", "email": "vikram.iyer@gmail.com",
        "phone": "+91-9844455566", "city": "Chennai, Tamil Nadu", "exp": 7,
        "primary": "Java",
        "summary": ("Java backend architect with 7+ years of experience. Deep expertise "
                    "in Java, Spring Boot and Java microservice design."),
        "skills": ["Java", "Spring Boot", "Hibernate", "Microservices", "Kafka",
                   "MySQL", "Docker", "Kubernetes"],
        "experience": [
            ("Lead Java Developer", "FinServe Systems, Chennai", "2019 - Present",
             ["Designed Java Spring Boot microservices for banking workflows.",
              "Tuned Java JVM performance for low-latency trading systems.",
              "Mentored a team of 6 Java engineers."]),
            ("Java Developer", "Cognizant, Chennai", "2016 - 2019",
             ["Developed Java REST services and batch jobs."]),
        ],
    },
    {
        "name": "Pooja Nair", "email": "pooja.nair@gmail.com",
        "phone": "+91-9855566677", "city": "Kochi, Kerala", "exp": 4,
        "primary": "Java",
        "summary": "Java developer with 4+ years building enterprise Java applications.",
        "skills": ["Java", "Spring", "JPA", "REST API", "Oracle", "Git", "Maven"],
        "experience": [
            ("Java Developer", "TCS, Kochi", "2020 - Present",
             ["Built Java Spring services for insurance products.",
              "Wrote JUnit tests for core Java modules."]),
        ],
    },
    {
        "name": "Aditya Rao", "email": "aditya.rao@gmail.com",
        "phone": "+91-9866677788", "city": "Bengaluru, Karnataka", "exp": 5,
        "primary": "React",
        "summary": ("Frontend engineer with 5+ years of experience specializing in "
                    "React, React Hooks and the React ecosystem."),
        "skills": ["React", "JavaScript", "TypeScript", "Redux", "Next.js",
                   "HTML/CSS", "Tailwind", "Git"],
        "experience": [
            ("Senior React Developer", "PixelForge, Bengaluru", "2020 - Present",
             ["Built reusable React component libraries used across 4 products.",
              "Improved React app performance with code-splitting and memoization.",
              "Migrated a legacy jQuery app to React."]),
            ("Frontend Developer", "Startup Hub, Bengaluru", "2018 - 2020",
             ["Developed responsive React interfaces."]),
        ],
    },
    {
        "name": "Neha Gupta", "email": "neha.gupta@gmail.com",
        "phone": "+91-9877788899", "city": "Noida, Uttar Pradesh", "exp": 3,
        "primary": "JavaScript",
        "summary": "Web developer with 3+ years of JavaScript experience.",
        "skills": ["JavaScript", "React", "Vue.js", "Node.js", "Express",
                   "MongoDB", "Git"],
        "experience": [
            ("JavaScript Developer", "WebMinds, Noida", "2021 - Present",
             ["Built interactive UIs with modern JavaScript and Vue.",
              "Created Node.js JavaScript APIs for internal tools."]),
        ],
    },
    {
        "name": "Karan Malhotra", "email": "karan.malhotra@gmail.com",
        "phone": "+91-9888899900", "city": "Gurugram, Haryana", "exp": 6,
        "primary": "Data Science",
        "summary": ("Data Science professional with 6+ years of experience in Data "
                    "Science, machine learning and predictive Data Science modeling."),
        "skills": ["Python", "Machine Learning", "Data Science", "TensorFlow",
                   "Pandas", "SQL", "Power BI"],
        "experience": [
            ("Senior Data Scientist", "Insightful AI, Gurugram", "2019 - Present",
             ["Led Data Science projects forecasting demand for retail clients.",
              "Built machine learning models improving accuracy by 22%.",
              "Productionized Data Science pipelines on AWS."]),
            ("Data Analyst", "Mu Sigma, Bengaluru", "2017 - 2019",
             ["Performed exploratory Data Science and reporting."]),
        ],
    },
    {
        "name": "Ananya Verma", "email": "ananya.verma@gmail.com",
        "phone": "+91-9899900011", "city": "Mumbai, Maharashtra", "exp": 4,
        "primary": "SQL",
        "summary": "Data engineer with 4+ years of strong SQL and database experience.",
        "skills": ["SQL", "PostgreSQL", "MySQL", "Python", "ETL", "Airflow",
                   "Power BI"],
        "experience": [
            ("Data Engineer", "DataWorks, Mumbai", "2020 - Present",
             ["Wrote complex SQL queries and stored procedures for reporting.",
              "Optimized SQL performance across large warehouse tables.",
              "Built SQL-based ETL workflows with Airflow."]),
        ],
    },
    {
        "name": "Rahul Saxena", "email": "rahul.saxena@gmail.com",
        "phone": "+91-9810011122", "city": "Pune, Maharashtra", "exp": 5,
        "primary": "AWS",
        "summary": ("DevOps engineer with 5+ years of experience operating AWS cloud "
                    "infrastructure and AWS-native services."),
        "skills": ["AWS", "Docker", "Kubernetes", "Terraform", "Jenkins",
                   "Linux", "Python", "CI/CD"],
        "experience": [
            ("DevOps Engineer", "CloudScale, Pune", "2020 - Present",
             ["Managed AWS infrastructure with Terraform across 3 regions.",
              "Built CI/CD pipelines deploying to AWS ECS and Lambda.",
              "Reduced AWS cloud cost by 30% through right-sizing."]),
            ("Systems Engineer", "Wipro, Pune", "2018 - 2020",
             ["Automated server provisioning and monitoring."]),
        ],
    },
    {
        "name": "Meera Joshi", "email": "meera.joshi@gmail.com",
        "phone": "+91-9820022233", "city": "Ahmedabad, Gujarat", "exp": 4,
        "primary": "Machine Learning",
        "summary": ("ML engineer with 4+ years of experience building Machine Learning "
                    "models and deploying Machine Learning systems to production."),
        "skills": ["Python", "Machine Learning", "Deep Learning", "PyTorch",
                   "Scikit-learn", "NLP", "SQL"],
        "experience": [
            ("Machine Learning Engineer", "NeuralEdge, Ahmedabad", "2021 - Present",
             ["Developed Machine Learning models for fraud detection.",
              "Built NLP Machine Learning pipelines for document parsing."]),
        ],
    },
    {
        "name": "Sanjana Reddy", "email": "sanjana.reddy@gmail.com",
        "phone": "+91-9830033344", "city": "Hyderabad, Telangana", "exp": 3,
        "primary": "Testing",
        "summary": "QA engineer with 3+ years of manual and automation Testing experience.",
        "skills": ["Selenium", "Testing", "Java", "TestNG", "JIRA", "Postman",
                   "API Testing"],
        "experience": [
            ("QA Engineer", "QualitySoft, Hyderabad", "2021 - Present",
             ["Built Selenium automation Testing suites for web apps.",
              "Performed API Testing and regression Testing each release."]),
        ],
    },
]


def _draw_resume(path, c_data):
    """Render one candidate dict to a PDF that the resume parser understands."""
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    left = inch * 0.8
    y = height - inch * 0.9
    line_h = 14

    def line(text, font="Helvetica", size=10, gap=line_h):
        nonlocal y
        c.setFont(font, size)
        c.drawString(left, y, text)
        y -= gap

    # Header
    line(c_data["name"], font="Helvetica-Bold", size=16, gap=20)
    line(f"{c_data['email']} | {c_data['phone']} | {c_data['city']}",
         size=9, gap=18)

    line("PROFESSIONAL SUMMARY", font="Helvetica-Bold", size=11)
    # wrap the summary at ~95 chars
    summary = c_data["summary"]
    while summary:
        chunk, summary = summary[:95], summary[95:]
        if summary and not summary[0].isspace() and " " in chunk:
            cut = chunk.rfind(" ")
            summary = chunk[cut:] + summary
            chunk = chunk[:cut]
        line(chunk.strip(), size=9)
    y -= 4

    line("KEY SKILLS", font="Helvetica-Bold", size=11)
    line(", ".join(c_data["skills"]), size=9, gap=18)

    line("WORK EXPERIENCE", font="Helvetica-Bold", size=11)
    for title, company, dates, bullets in c_data["experience"]:
        line(f"{title}  |  {dates}", font="Helvetica-Bold", size=10)
        line(company, size=9)
        for b in bullets:
            line(f"- {b}", size=9)
        y -= 4

    line("EDUCATION", font="Helvetica-Bold", size=11)
    line("B.Tech in Computer Science", size=9)

    c.save()


class Command(BaseCommand):
    help = "Generate sample candidate resume PDFs for the employer candidate search."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete previously seeded sample resumes before generating.",
        )

    def handle(self, *args, **options):
        if canvas is None:
            self.stderr.write(self.style.ERROR(
                "reportlab is not installed. Run: pip install reportlab"
            ))
            return

        resumes_dir = os.path.join(str(settings.MEDIA_ROOT), "resumes")
        os.makedirs(resumes_dir, exist_ok=True)

        if options["clear"]:
            removed = 0
            for fn in os.listdir(resumes_dir):
                if fn.startswith(SEED_PREFIX):
                    os.remove(os.path.join(resumes_dir, fn))
                    removed += 1
            self.stdout.write(self.style.WARNING(
                f"Removed {removed} previously seeded resume(s)."
            ))

        created = 0
        for i, cand in enumerate(CANDIDATES, start=1):
            safe_name = cand["name"].replace(" ", "_")
            filename = f"{SEED_PREFIX}{i:02d}_{safe_name}.pdf"
            _draw_resume(os.path.join(resumes_dir, filename), cand)
            created += 1
            self.stdout.write(
                f"  + {filename}  ({cand['primary']}, {cand['exp']}+ yrs)"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Generated {created} sample resume(s) in {resumes_dir}"
        ))

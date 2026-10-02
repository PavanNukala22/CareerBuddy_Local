"""
Django management command to seed 100 Non-IT, Voice Process, Non-Voice Process,
and Service Desk (L1/L2) interview questions into FAQQuestion database table.

Usage:
    python manage.py seed_process_questions
"""

from django.core.management.base import BaseCommand
from career_app.models import FAQQuestion

PROCESS_QUESTIONS = [
    # ─── 1. VOICE PROCESSES ───────────────────────────────────────────────────
    # Customer Support
    {"topic": "customer support", "difficulty": "Easy", "question_text": "How do you handle an extremely angry customer on a call while maintaining professional composure?"},
    {"topic": "customer support", "difficulty": "Easy", "question_text": "What does First Call Resolution (FCR) mean to you, and why is it important in customer support?"},
    {"topic": "customer support", "difficulty": "Intermediate", "question_text": "Describe a time when you had to say 'no' to a customer request while keeping them satisfied."},
    {"topic": "customer support", "difficulty": "Intermediate", "question_text": "How do you control call duration (AHT) without making the customer feel rushed?"},
    {"topic": "customer support", "difficulty": "Hard", "question_text": "What steps do you take when a customer insists on speaking with a supervisor or escalation manager?"},

    # Technical Support (Voice)
    {"topic": "technical support", "difficulty": "Easy", "question_text": "How do you explain a complex technical solution to a non-technical customer over the phone?"},
    {"topic": "technical support", "difficulty": "Easy", "question_text": "What are the essential steps you take when a user calls saying their internet connection is not working?"},
    {"topic": "technical support", "difficulty": "Intermediate", "question_text": "How do you troubleshoot a phone call where the user cannot hear you or audio is distorted?"},
    {"topic": "technical support", "difficulty": "Intermediate", "question_text": "Describe your process for taking remote control of a user's computer while guiding them verbally."},
    {"topic": "technical support", "difficulty": "Hard", "question_text": "How do you handle an outage situation where multiple users call simultaneously about the same system failure?"},

    # Sales
    {"topic": "sales", "difficulty": "Easy", "question_text": "How do you introduce yourself and open a cold sales call to capture the prospect's interest in the first 10 seconds?"},
    {"topic": "sales", "difficulty": "Easy", "question_text": "How do you respond when a customer says 'Your product is too expensive' during a sales pitch?"},
    {"topic": "sales", "difficulty": "Intermediate", "question_text": "What is the difference between features and benefits, and how do you pitch benefits to a buyer?"},
    {"topic": "sales", "difficulty": "Intermediate", "question_text": "Describe your strategy for overcoming customer hesitation and closing a sale on the phone."},
    {"topic": "sales", "difficulty": "Hard", "question_text": "How do you handle a scenario where a prospect agrees to everything but delays signing or making a payment?"},

    # Appointment Setting
    {"topic": "appointment setting", "difficulty": "Easy", "question_text": "What is the primary objective of an appointment setting call, and how do you qualify a prospect?"},
    {"topic": "appointment setting", "difficulty": "Easy", "question_text": "How do you handle gatekeepers (exec assistants/receptionists) to reach decision-makers?"},
    {"topic": "appointment setting", "difficulty": "Intermediate", "question_text": "How do you handle a prospect who says 'Send me an email first' before scheduling a demo call?"},
    {"topic": "appointment setting", "difficulty": "Intermediate", "question_text": "What details do you confirm before locking in an appointment date on the executive's calendar?"},
    {"topic": "appointment setting", "difficulty": "Hard", "question_text": "How do you reduce no-show rates for scheduled sales or discovery appointments?"},

    # ─── 2. NON-VOICE PROCESSES ───────────────────────────────────────────────
    # Email Support
    {"topic": "email support", "difficulty": "Easy", "question_text": "What are the key elements of professional email etiquette when replying to customer queries?"},
    {"topic": "email support", "difficulty": "Easy", "question_text": "How do you structure an email response for a customer reporting a billing error?"},
    {"topic": "email support", "difficulty": "Intermediate", "question_text": "How do you handle an ambiguous email request where the customer didn't provide necessary details?"},
    {"topic": "email support", "difficulty": "Intermediate", "question_text": "What strategies do you use to maintain high accuracy and grammar standards while handling large email volumes?"},
    {"topic": "email support", "difficulty": "Hard", "question_text": "How do you write a formal apology email on behalf of the company for a major service disruption?"},

    # Chat Support
    {"topic": "chat support", "difficulty": "Easy", "question_text": "How do you manage 3 or 4 simultaneous live chats without delaying response times?"},
    {"topic": "chat support", "difficulty": "Easy", "question_text": "What is the importance of canned responses (templates) in chat support, and when should you avoid them?"},
    {"topic": "chat support", "difficulty": "Intermediate", "question_text": "How do you convey warmth and empathy in a text chat without using voice tone?"},
    {"topic": "chat support", "difficulty": "Intermediate", "question_text": "What do you do if a customer becomes unresponsive during an active live chat session?"},
    {"topic": "chat support", "difficulty": "Hard", "question_text": "How do you smoothly transition a chat conversation to a phone call or email ticket when issues get complex?"},

    # Back Office
    {"topic": "back office", "difficulty": "Easy", "question_text": "What methods do you use to maintain 100% data accuracy during repetitive back-office tasks?"},
    {"topic": "back office", "difficulty": "Easy", "question_text": "How do you prioritize daily back-office tasks when facing multiple tight deadlines?"},
    {"topic": "back office", "difficulty": "Intermediate", "question_text": "What steps do you take when you spot an error in a previously processed data batch?"},
    {"topic": "back office", "difficulty": "Intermediate", "question_text": "How do you ensure strict compliance with client SLAs and confidentiality guidelines?"},
    {"topic": "back office", "difficulty": "Hard", "question_text": "Describe a scenario where you identified a bottleneck in a back-office process and suggested an improvement."},

    # Data Processing
    {"topic": "data processing", "difficulty": "Easy", "question_text": "What techniques do you use to verify data integrity before entering information into a database?"},
    {"topic": "data processing", "difficulty": "Easy", "question_text": "Which MS Excel or Google Sheets functions do you use most frequently for data cleanup (e.g. VLOOKUP, TRIM, Remove Duplicates)?"},
    {"topic": "data processing", "difficulty": "Intermediate", "question_text": "How do you process large volumes of structured data accurately under time constraints?"},
    {"topic": "data processing", "difficulty": "Intermediate", "question_text": "What is data validation, and how do you set up validation rules to prevent incorrect input?"},
    {"topic": "data processing", "difficulty": "Hard", "question_text": "How do you handle discrepancy reconciliation when two data sources provide conflicting records?"},

    # HR Shared Services
    {"topic": "hr shared services", "difficulty": "Easy", "question_text": "What are the core responsibilities of an HR Shared Services specialist?"},
    {"topic": "hr shared services", "difficulty": "Easy", "question_text": "How do you handle a sensitive inquiry from an employee regarding payroll or leave balance errors?"},
    {"topic": "hr shared services", "difficulty": "Intermediate", "question_text": "What is an HR Ticketing system, and how do you track employee SLA resolutions?"},
    {"topic": "hr shared services", "difficulty": "Intermediate", "question_text": "How do you ensure strict data privacy and confidentiality when handling employee PII records?"},
    {"topic": "hr shared services", "difficulty": "Hard", "question_text": "How do you manage onboarding documentation verification for multi-country remote hires?"},

    # ─── 3. SERVICE DESK & TECH SUPPORT (L1/L2) ──────────────────────────────
    # IT Help Desk Analyst
    {"topic": "it help desk analyst", "difficulty": "Easy", "question_text": "What is the standard procedure for verifying a user's identity before resetting their corporate password?"},
    {"topic": "it help desk analyst", "difficulty": "Easy", "question_text": "How do you categorize and assign priority levels (P1, P2, P3, P4) to incoming IT tickets?"},
    {"topic": "it help desk analyst", "difficulty": "Intermediate", "question_text": "What basic steps do you follow in Active Directory when a user is locked out of their domain account?"},
    {"topic": "it help desk analyst", "difficulty": "Intermediate", "question_text": "How do you troubleshoot a user unable to authenticate to the company VPN from home?"},
    {"topic": "it help desk analyst", "difficulty": "Hard", "question_text": "What steps do you take when escalating a critical P1 ticket to L3 engineering teams?"},

    # Service Desk Analyst
    {"topic": "service desk analyst", "difficulty": "Easy", "question_text": "What is the difference between an Incident and a Service Request according to ITIL guidelines?"},
    {"topic": "service desk analyst", "difficulty": "Easy", "question_text": "What IT Service Management (ITSM) tools have you used (e.g. ServiceNow, Jira Service Management, Remedy)?"},
    {"topic": "service desk analyst", "difficulty": "Intermediate", "question_text": "How do you document resolution notes in a ticket so that the knowledge base remains updated?"},
    {"topic": "service desk analyst", "difficulty": "Intermediate", "question_text": "What is a Known Error Database (KEDB), and how does it speed up ticket resolution?"},
    {"topic": "service desk analyst", "difficulty": "Hard", "question_text": "How do you handle major incident notifications and stakeholder communication during system outages?"},

    # Desktop Support Engineer
    {"topic": "desktop support engineer", "difficulty": "Easy", "question_text": "What commands do you run in Windows Command Prompt to check IP config, release, and renew IP addresses?"},
    {"topic": "desktop support engineer", "difficulty": "Easy", "question_text": "How do you troubleshoot a desktop computer that powers on but displays a blank black screen?"},
    {"topic": "desktop support engineer", "difficulty": "Intermediate", "question_text": "What steps do you follow when troubleshooting network printer connectivity on a local office network?"},
    {"topic": "desktop support engineer", "difficulty": "Intermediate", "question_text": "How do you perform OS deployment or reimaging using tools like WDS or SCCM?"},
    {"topic": "desktop support engineer", "difficulty": "Hard", "question_text": "How do you diagnose Blue Screen of Death (BSOD) stop errors and repair corrupted system files?"},

    # Application Support Engineer
    {"topic": "application support engineer", "difficulty": "Easy", "question_text": "How do you check application error logs on Linux or Windows servers when an app crashes?"},
    {"topic": "application support engineer", "difficulty": "Easy", "question_text": "What basic SQL queries do you use to verify data records in an application database?"},
    {"topic": "application support engineer", "difficulty": "Intermediate", "question_text": "How do you troubleshoot HTTP 500 Internal Server Error reported by web application users?"},
    {"topic": "application support engineer", "difficulty": "Intermediate", "question_text": "What is the role of environment variables and configuration files in application deployment?"},
    {"topic": "application support engineer", "difficulty": "Hard", "question_text": "How do you investigate high memory usage or thread locks in a production application server?"},

    # Customer Technical Support Specialist
    {"topic": "customer technical support specialist", "difficulty": "Easy", "question_text": "How do you use browser Developer Tools (Network/Console tabs) to troubleshoot client web app issues?"},
    {"topic": "customer technical support specialist", "difficulty": "Easy", "question_text": "What steps do you take when a user reports that a web page button is unresponsive?"},
    {"topic": "customer technical support specialist", "difficulty": "Intermediate", "question_text": "How do you reproduce a customer-reported bug and create a detailed report for the engineering team?"},
    {"topic": "customer technical support specialist", "difficulty": "Intermediate", "question_text": "What steps do you take to troubleshoot single sign-on (SSO) login failures reported by clients?"},
    {"topic": "customer technical support specialist", "difficulty": "Hard", "question_text": "How do you handle an API integration failure reported by a client developer using your platform?"},

    # Network Support Engineer
    {"topic": "network support engineer", "difficulty": "Easy", "question_text": "What is the difference between IPv4 and IPv6 addresses?"},
    {"topic": "network support engineer", "difficulty": "Easy", "question_text": "How do you use the 'ping' and 'traceroute/tracert' commands to test network connectivity?"},
    {"topic": "network support engineer", "difficulty": "Intermediate", "question_text": "What is DNS resolution, and how do you clear/flush DNS cache when website names fail to resolve?"},
    {"topic": "network support engineer", "difficulty": "Intermediate", "question_text": "What is the function of DHCP, and what happens when DHCP scope is exhausted?"},
    {"topic": "network support engineer", "difficulty": "Hard", "question_text": "How do you troubleshoot VLAN routing or subnet mask mismatch issues on a corporate switch?"},

    # Cloud Support Associate
    {"topic": "cloud support associate", "difficulty": "Easy", "question_text": "What are the core differences between IaaS, PaaS, and SaaS cloud models?"},
    {"topic": "cloud support associate", "difficulty": "Easy", "question_text": "How do you check cloud server/instance CPU, memory, and status checks in AWS or Azure console?"},
    {"topic": "cloud support associate", "difficulty": "Intermediate", "question_text": "What is cloud object storage (e.g. AWS S3, Azure Blob), and how do you configure bucket permissions?"},
    {"topic": "cloud support associate", "difficulty": "Intermediate", "question_text": "How do you troubleshoot security group rules when a web server on AWS EC2 is unreachable over port 80/443?"},
    {"topic": "cloud support associate", "difficulty": "Hard", "question_text": "What steps do you take when a cloud database instance triggers a high latency or storage full alert?"},

    # GIS Executive
    {"topic": "gis executive", "difficulty": "Easy", "question_text": "What is GIS (Geographic Information System), and what are vector vs raster data formats?"},
    {"topic": "gis executive", "difficulty": "Easy", "question_text": "Which GIS software applications have you worked with (e.g. QGIS, ArcGIS)?"},
    {"topic": "gis executive", "difficulty": "Intermediate", "question_text": "What is a Coordinate Reference System (CRS), and why is reprojecting layers important in GIS analysis?"},
    {"topic": "gis executive", "difficulty": "Intermediate", "question_text": "How do you digitize map features accurately while avoiding spatial topological errors?"},
    {"topic": "gis executive", "difficulty": "Hard", "question_text": "How do you perform spatial join and buffer analysis to identify optimal location sites?"},

    # AML/KYC Executive
    {"topic": "aml/kyc executive", "difficulty": "Easy", "question_text": "What is the purpose of Know Your Customer (KYC) and Anti-Money Laundering (AML) regulations?"},
    {"topic": "aml/kyc executive", "difficulty": "Easy", "question_text": "What standard identity documents are required for individual customer verification?"},
    {"topic": "aml/kyc executive", "difficulty": "Intermediate", "question_text": "What is a Politically Exposed Person (PEP), and why requires enhanced due diligence (EDD)?"},
    {"topic": "aml/kyc executive", "difficulty": "Intermediate", "question_text": "What red flags indicate potential suspicious financial transactions or structuring?"},
    {"topic": "aml/kyc executive", "difficulty": "Hard", "question_text": "When and how do you file a Suspicious Activity Report (SAR/STR) with financial compliance authorities?"},

    # Content Moderator
    {"topic": "content moderator", "difficulty": "Easy", "question_text": "What is the primary role of a content moderator in digital platforms?"},
    {"topic": "content moderator", "difficulty": "Easy", "question_text": "How do you remain objective and impartial when reviewing user-generated content against policy guidelines?"},
    {"topic": "content moderator", "difficulty": "Intermediate", "question_text": "How do you distinguish between constructive free speech and hate speech/harassment?"},
    {"topic": "content moderator", "difficulty": "Intermediate", "question_text": "What steps do you take when encountering high-priority emergency content (e.g. self-harm or imminent danger threats)?"},
    {"topic": "content moderator", "difficulty": "Hard", "question_text": "How do you maintain high decision accuracy and mental wellness while reviewing large volumes of flagged content?"},
]


class Command(BaseCommand):
    help = "Seed 100 Non-IT, Voice, Non-Voice, and Service Desk (L1/L2) questions into FAQQuestion."

    def handle(self, *args, **options):
        to_create = []
        for q in PROCESS_QUESTIONS:
            to_create.append(
                FAQQuestion(
                    topic=q["topic"].lower().strip(),
                    question_text=q["question_text"].strip()[:500],
                    difficulty=q["difficulty"].strip(),
                )
            )

        before = FAQQuestion.objects.count()
        FAQQuestion.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=1000)
        after = FAQQuestion.objects.count()

        created_count = after - before
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully seeded {created_count} process/service desk questions into FAQQuestion! (Total in DB: {after})"
            )
        )

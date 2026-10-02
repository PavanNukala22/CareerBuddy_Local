"""
End-to-end validation of the 4-candidate-type interview question generation,
against the REAL production code path: creates real Resume/JobDescription/
ResumeInterviewSession/ResumeQuestion DB rows and calls the exact same
functions career_app/views.py uses (_ensure_resume_interview_questions's
logic, then the same next_domain_difficulty/select_next_domain_question loop
resume_get_next_question uses for Q11-20), for one synthetic resume per
candidate type. Test data only — created objects are deleted at the end.
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'business_english_lms.settings')
django.setup()

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

from core.models import Resume, JobDescription
from career_app.models import ResumeInterviewSession, ResumeQuestion
from career_app.resume_utils import (
    generate_interview_questions, extract_experience_years,
    classify_experience_level, classify_candidate_type,
    next_domain_difficulty, select_next_domain_question,
)

User = get_user_model()

RESUMES = {
    'IT_EXPERIENCED': {
        'skills': ['Python', 'Django', 'React', 'PostgreSQL', 'Docker', 'AWS'],
        'text': """
Rahul Sharma
Senior Software Engineer

PROFESSIONAL EXPERIENCE
Software Engineer, TechNova Solutions (2021 - Present) - 4 years
- Built and maintained backend REST APIs using Python and Django for a fintech platform.
- Led migration of monolith services to a microservices architecture on AWS using Docker and Kubernetes.
- Mentored 2 junior developers and conducted code reviews.
- Optimized PostgreSQL queries, reducing average API response time by 35%.

Software Developer, ByteCraft Pvt Ltd (2019 - 2021)
- Developed React-based dashboards for internal analytics tools.
- Implemented CI/CD pipelines using GitHub Actions.

SKILLS
Python, Django, React, JavaScript, PostgreSQL, Docker, Kubernetes, AWS, Git, REST APIs

EDUCATION
B.Tech in Computer Science, XYZ University (2015-2019)
""",
    },
    'IT_FRESHER': {
        'skills': ['Java', 'Spring Boot', 'MySQL', 'HTML', 'CSS'],
        'text': """
Ananya Reddy
Aspiring Software Developer

EDUCATION
B.Tech in Computer Science, ABC Institute of Technology (2021-2025)
CGPA: 8.7/10

ACADEMIC PROJECTS
Final Year Project: Online Library Management System
- Built a full-stack web application using Java Spring Boot and MySQL.
- Implemented user authentication, book search, and fine calculation modules.
- Deployed the project on a college server for demonstration.

Personal Project: Expense Tracker Android App
- Developed an Android app in Java to track daily expenses with SQLite storage.

INTERNSHIP
Summer Intern, CodeBridge Labs (2 months, 2024)
- Assisted in writing unit tests for an internal Java-based tool.

CERTIFICATIONS
- Oracle Certified Associate, Java SE 8 Programmer
- freeCodeCamp - Responsive Web Design

SKILLS
Java, Spring Boot, MySQL, HTML, CSS, Git, Data Structures & Algorithms
""",
    },
    'NON_IT_EXPERIENCED': {
        'skills': ['Recruitment', 'Employee Relations', 'Payroll', 'Onboarding'],
        'text': """
Priya Nair
Senior HR Executive

PROFESSIONAL EXPERIENCE
HR Executive, Meridian Manufacturing Ltd (2020 - Present) - 4 years
- Managed end-to-end recruitment for factory and corporate staff, closing 150+ positions.
- Handled employee relations, grievance redressal and performance management cycles.
- Coordinated monthly payroll processing for 300+ employees in coordination with finance.
- Rolled out a new employee onboarding program that cut new-hire ramp-up time by 20%.

HR Associate, Meridian Manufacturing Ltd (2018 - 2020)
- Supported recruitment coordination and maintained employee records.

EDUCATION
MBA in Human Resource Management, State Business School (2016-2018)
BA in Psychology, City College (2013-2016)

SKILLS
Recruitment, Employee Relations, Payroll Processing, Onboarding, HR Policies, Performance Management
""",
    },
    'NON_IT_FRESHER': {
        'skills': ['Digital Marketing', 'Social Media', 'Market Research'],
        'text': """
Karthik Iyer
Marketing Graduate

EDUCATION
BBA in Marketing, Coastal Business College (2021-2024)

ACADEMIC PROJECTS
Final Year Project: Social Media Marketing Strategy for a Local Bakery
- Conducted market research and designed a 3-month social media campaign plan.
- Analyzed competitor campaigns and proposed a content calendar.

INTERNSHIP
Marketing Intern, BrightAds Agency (3 months, 2024)
- Assisted in creating content for Instagram and Facebook campaigns.
- Compiled weekly performance reports using basic analytics tools.

CERTIFICATIONS
- Google Digital Marketing & E-commerce Certificate
- HubSpot Content Marketing Certification

SKILLS
Digital Marketing, Social Media Management, Market Research, Content Creation, MS Excel
""",
    },
}

CATEGORY_MAP = {
    'IT_EXPERIENCED':     {'Behavioural': 5, 'Experience': 5, 'Domain': 10},
    'IT_FRESHER':         {'Behavioural': 5, 'Academic/Project': 5, 'Domain': 10},
    'NON_IT_EXPERIENCED': {'Behavioural': 5, 'Experience': 5, 'Domain': 10},
    'NON_IT_FRESHER':     {'Behavioural': 5, 'Academic/Project': 5, 'Domain': 10},
}


def run_one(label, skills, resume_text, user):
    resume = Resume.objects.create(user=user)
    resume.file.save(f'{label}.txt', ContentFile(resume_text.encode('utf-8')))
    resume.extracted_text = resume_text
    resume.save(update_fields=['extracted_text'])

    jd = JobDescription.objects.create(user=user, text='General Resume Analysis')

    years = extract_experience_years(resume_text)
    exp_level = classify_experience_level(years)
    candidate_type = classify_candidate_type(resume_text, skills, years=years)

    session = ResumeInterviewSession.objects.create(
        resume=resume, job_description=jd, matching_skills=skills,
        experience_level=exp_level,
    )

    # Q1-10, exactly as _ensure_resume_interview_questions() does (domain_count=0).
    raw = generate_interview_questions(
        resume_text, jd.text, skills=skills, user=user, domain_count=0,
    )
    for i, q in enumerate(raw):
        ResumeQuestion.objects.create(
            session=session, question_text=q.get('question', ''),
            topic=q.get('topic', 'General'), difficulty=q.get('difficulty', 'Easy'),
            question_type=q.get('question_type', 'theory'), order=i,
        )

    # Q11-20, exactly as resume_get_next_question does: one at a time, adaptive.
    for idx in range(len(raw), 20):
        difficulty = next_domain_difficulty(session)
        next_q = select_next_domain_question(session, difficulty)
        if next_q is None:
            break
        ResumeQuestion.objects.create(
            session=session, question_text=next_q.get('question', ''),
            topic=next_q.get('topic', 'Domain'), difficulty=next_q.get('difficulty', difficulty),
            question_type=next_q.get('question_type', 'theory'), order=idx,
        )

    questions = list(session.questions.order_by('order'))
    print(f'\n=== {label} (resume: computed as {candidate_type}, years={years}, level={exp_level}) ===')
    print(f'Total questions: {len(questions)}')

    counts = {'Behavioural': 0, 'Experience': 0, 'Academic/Project': 0, 'Domain': 0}
    texts_seen = set()
    dup_found = False
    for q in questions:
        if q.order < 5:
            counts['Behavioural'] += 1
        elif q.order < 10:
            # topic is either 'Experience' or 'Academic/Project'
            key = 'Academic/Project' if 'academic' in q.topic.lower() or 'project' in q.topic.lower() else 'Experience'
            counts[key] += 1
        else:
            counts['Domain'] += 1
        if q.question_text in texts_seen:
            dup_found = True
        texts_seen.add(q.question_text)

    expected = CATEGORY_MAP[candidate_type]
    print(f'Category counts: Behavioural={counts["Behavioural"]}, '
          f'{"Experience" if expected.get("Experience") else "Academic/Project"}='
          f'{counts["Experience"] or counts["Academic/Project"]}, Domain={counts["Domain"]}')
    print(f'Exact duplicates found: {dup_found}')

    ok = (
        len(questions) == 20
        and counts['Behavioural'] == expected['Behavioural']
        and (counts.get('Experience', 0) + counts.get('Academic/Project', 0)) == (
            expected.get('Experience', 0) + expected.get('Academic/Project', 0)
        )
        and counts['Domain'] == expected['Domain']
        and not dup_found
    )
    print('RESULT:', 'PASS' if ok else 'FAIL')

    for q in questions[:3]:
        print(f'  [{q.order}] ({q.topic}/{q.difficulty}) {q.question_text[:80]}')
    print('  ...')
    for q in questions[10:13]:
        print(f'  [{q.order}] ({q.topic}/{q.difficulty}) {q.question_text[:80]}')

    return ok, session, resume, jd


def main():
    user = User.objects.filter(is_superuser=False, is_active=True).first()
    results = []
    cleanup = []
    for label, data in RESUMES.items():
        ok, session, resume, jd = run_one(label, data['skills'], data['text'], user)
        results.append((label, ok))
        cleanup.append((session, resume, jd))

    print('\n\n=== SUMMARY ===')
    for label, ok in results:
        print(f'{label}: {"PASS" if ok else "FAIL"}')

    for session, resume, jd in cleanup:
        session.delete()
        resume.file.delete(save=False)
        resume.delete()
        jd.delete()
    print('\nTest data cleaned up.')


if __name__ == '__main__':
    main()

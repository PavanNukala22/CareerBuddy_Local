# Resume Builder & AI Interview Integration Guide

This package provides a complete Resume Builder with ATS scoring, Job Matching, and an AI-powered Interview system that uses a database of 6,900+ technical questions.

## Contents
- `core_logic/resume_utils.py`: Text extraction (PDF/DOCX) and AI analysis logic.
- `core_logic/models.py`: Database models for Resumes, JDs, Interviews, and Questions.
- `core_logic/views.py`: View logic for the entire workflow.
- `templates/`: HTML templates for the builder and interview UI.
- `data/interview_questions.csv`: A database of 6,935 technical questions across various topics.

## Integration Steps

### 1. File Placement
- Copy `resume_utils.py`, `models.py`, and `views.py` into your project (ideally within a `career` or `core` app).
- Copy `templates/` to your project's template directory.
- Place `interview_questions.csv` in a directory accessible to your import script.

### 2. Database Setup
- Register the models in your `INSTALLED_APPS`.
- Run migrations: `python manage.py makemigrations` and `python manage.py migrate`.

### 3. Importing Questions
Use the following command in `python manage.py shell` to load the CSV data into your database:

```python
import csv
from core.models import FAQQuestion
with open('data/interview_questions.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        FAQQuestion.objects.get_or_create(
            topic=row['topic'],
            difficulty=row['difficulty'],
            question_text=row['question_text']
        )
```

### 4. URL Configuration
Register the following routes:

```python
path('resume-builder/', views.resume_builder_home, name='resume_builder'),
path('resume-builder/match/', views.resume_job_match, name='resume_job_match'),
path('resume-builder/start-interview/', views.resume_start_interview, name='resume_start_interview'),
path('resume-builder/interview/chat/', views.resume_interview_chat, name='resume_interview_chat'),
path('resume-builder/get-question/', views.resume_get_next_question, name='resume_get_next_question'),
path('resume-builder/submit-answer/', views.resume_submit_answer, name='resume_submit_answer'),
path('resume-builder/analytics/', views.resume_analytics, name='resume_analytics'),
```

## Features
- **ATS Scoring**: Analyzes resumes for keyword density and professional standards.
- **Job Matching**: Compares resumes against JDs to find skill gaps and matches.
- **AI Interview**: Conducts a structured interview based on extracted skills using the 6,900+ question database.
- **Evaluation**: Scores user answers and provides constructive AI feedback.

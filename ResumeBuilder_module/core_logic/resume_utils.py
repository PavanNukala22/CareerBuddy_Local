"""
Utility functions for the Resume Builder feature.
Uses the existing SARVAM_API_KEY from the environment.
"""
import json
import logging
import os
import re
import requests

logger = logging.getLogger(__name__)


def get_sarvam_api_key():
    return os.environ.get('SARVAM_API_KEY', '')


# ─── PDF extraction engines (tried in order until one yields text) ─────────────

def _extract_with_pypdf_layout(file_path):
    """pypdf v4+ layout-aware extraction – best for multi-column resumes."""
    import pypdf  # type: ignore
    text_parts = []
    reader = pypdf.PdfReader(file_path)
    for page in reader.pages:
        try:
            page_text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_with_pypdf_plain(file_path):
    """pypdf plain extraction – fast, works for most standard PDFs."""
    import pypdf  # type: ignore
    text_parts = []
    reader = pypdf.PdfReader(file_path)
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_with_pdfplumber(file_path):
    """pdfplumber – excels at template-heavy & table-rich PDFs."""
    import pdfplumber  # type: ignore
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_with_pdfminer(file_path):
    """pdfminer.six – handles complex font encoding where others produce garbage."""
    from pdfminer.high_level import extract_text as pdfminer_extract  # type: ignore
    text = pdfminer_extract(file_path) or ""
    return text.strip()


def _extract_with_pypdf2(file_path):
    """PyPDF2 legacy – last resort for old-format PDFs."""
    import PyPDF2  # type: ignore
    text_parts = []
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


_PDF_ENGINES = [
    _extract_with_pypdf_layout,
    _extract_with_pypdf_plain,
    _extract_with_pdfplumber,
    _extract_with_pdfminer,
    _extract_with_pypdf2,
]


def extract_text_from_pdf(file_path):
    """Try multiple PDF extraction engines in order."""
    last_error = None
    for engine in _PDF_ENGINES:
        try:
            text = engine(file_path)
            if text and len(text.strip()) > 30:
                logger.info(f"PDF extracted via {engine.__name__}, length={len(text)}")
                return text
        except Exception as exc:
            last_error = exc
            logger.warning(f"PDF engine {engine.__name__} failed: {exc}")

    if last_error is not None:
        logger.error(f"All PDF engines failed: {last_error}")
        return f'Error reading PDF: {last_error}'

    logger.error("PDF has no extractable text (likely a scanned/image file).")
    return ''


def extract_text_from_docx(file_path):
    """Extract all text from a DOCX including table cells."""
    try:
        import docx  # type: ignore
        doc = docx.Document(file_path)
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    cell_text = cell.text.strip()
                    if cell_text and cell_text not in parts:
                        parts.append(cell_text)
        return '\n'.join(parts)
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        return f'Error reading DOCX: {e}'


def _sarvam_chat(prompt):
    """Send a prompt to Sarvam AI chat completions and return the raw text.
    Retries up to 3 times with exponential backoff on timeout/connection errors.
    """
    import time
    from django.conf import settings
    api_key = getattr(settings, 'SARVAM_API_KEY', None) or get_sarvam_api_key()
    if not api_key:
        raise ValueError('SARVAM_API_KEY is missing.')
    headers = {
        'api-subscription-key': api_key,
        'Content-Type': 'application/json',
    }
    data = {
        'model': getattr(settings, 'SARVAM_MODEL', 'sarvam-105b'),
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.7,
    }

    max_retries = 1
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                'https://api.sarvam.ai/v1/chat/completions',
                headers=headers, json=data, timeout=10,
            )
            if response.status_code != 200:
                raise Exception(f"Sarvam API failed with {response.status_code}: {response.text}")
            return response.json()['choices'][0]['message']['content']
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            logger.warning(f"Sarvam API attempt {attempt}/{max_retries} failed: {e}")
        except Exception:
            raise

    raise Exception(f"Sarvam API timed out: {last_error}")


def _parse_json_response(text):
    """Extract the first valid JSON object/array even if extra text surrounds it."""
    cleaned = str(text or '').strip()
    if not cleaned:
        raise ValueError('Empty AI response.')

    fenced_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned, flags=re.IGNORECASE)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    decoder = json.JSONDecoder()
    candidates = []
    seen = set()

    def add_candidate(value):
        candidate = str(value or '').strip()
        if candidate and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)

    add_candidate(cleaned)
    json_starts = [index for index in (cleaned.find('['), cleaned.find('{')) if index >= 0]
    if json_starts:
        add_candidate(cleaned[min(json_starts):])

    for candidate in candidates:
        try:
            parsed, _ = decoder.raw_decode(candidate)
            return parsed
        except json.JSONDecodeError:
            continue

    for match in re.finditer(r'[\[{]', cleaned):
        try:
            parsed, _ = decoder.raw_decode(cleaned[match.start():])
            return parsed
        except json.JSONDecodeError:
            continue

    raise ValueError('Could not parse JSON from AI response.')


def _normalize_interview_questions(raw_questions):
    normalized = []
    for item in raw_questions or []:
        topic = 'General'
        question = ''

        if isinstance(item, str):
            question = item
        elif isinstance(item, dict):
            topic = str(item.get('topic') or 'General')
            question = str(
                item.get('question')
                or item.get('text')
                or item.get('prompt')
                or ''
            )

        topic = re.sub(r'\s+', ' ', topic).strip()[:80] or 'General'
        question = re.sub(r'\s+', ' ', question).strip()[:500]
        lowered = question.lower()

        if not question:
            continue
        if lowered.startswith('failed to generate questions:'):
            continue
        if lowered == 'could not parse questions.':
            continue

        normalized.append({'topic': topic, 'question': question})

    return normalized[:5]


def _fallback_interview_questions(resume_text, job_description):
    resume_hint = 'your resume'
    job_hint = 'this role'

    if str(resume_text or '').strip():
        resume_hint = 'your recent projects and experience'
    if str(job_description or '').strip():
        job_hint = 'the job description you applied for'

    return [
        {
            'topic': 'Introduction',
            'question': f'Tell me about yourself and highlight the parts of {resume_hint} that best match {job_hint}.',
        },
        {
            'topic': 'Experience',
            'question': 'Which project or responsibility from your background are you most proud of, and what was your exact contribution?',
        },
        {
            'topic': 'Technical',
            'question': 'Describe one technical challenge you faced in a project, how you solved it, and what you learned from it.',
        },
        {
            'topic': 'Problem Solving',
            'question': 'Tell me about a time you had to learn something quickly to complete a task successfully.',
        },
        {
            'topic': 'Behavioral',
            'question': 'Why do you want this role, and how would you add value in your first few months?',
        },
    ]



# ─── Comprehensive skill vocabulary for local (offline) analysis ──────────────
_TECH_SKILLS = [
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php',
    'swift', 'kotlin', 'go', 'rust', 'scala', 'matlab', 'perl', 'bash',
    'shell', 'powershell', 'vba', 'dart',
    'html', 'css', 'react', 'angular', 'vue', 'jquery', 'bootstrap', 'tailwind',
    'sass', 'webpack', 'node.js', 'nodejs', 'express', 'django', 'flask',
    'fastapi', 'spring', 'laravel', 'rails', 'asp.net', 'next.js',
    'machine learning', 'deep learning', 'nlp', 'natural language processing',
    'computer vision', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
    'pandas', 'numpy', 'matplotlib', 'spark', 'hadoop',
    'data analysis', 'data science', 'data engineering', 'etl',
    'power bi', 'tableau', 'excel', 'statistics',
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'terraform',
    'ansible', 'jenkins', 'ci/cd', 'devops', 'linux', 'unix', 'nginx',
    'microservices', 'serverless', 'git', 'github', 'gitlab',
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
    'oracle', 'sqlite', 'dynamodb', 'cassandra', 'firebase',
    'android', 'ios', 'react native', 'flutter',
    'agile', 'scrum', 'kanban', 'jira', 'confluence', 'trello',
    'project management', 'product management',
    'networking', 'rest api', 'graphql', 'cybersecurity',
    'microsoft office', 'google workspace', 'crm', 'salesforce', 'sap', 'erp',
    'business analysis', 'financial analysis', 'accounting', 'supply chain',
    'leadership', 'communication', 'teamwork', 'problem solving',
    'critical thinking', 'time management', 'adaptability', 'creativity',
    'collaboration', 'presentation', 'negotiation', 'mentoring',
    'customer service', 'stakeholder management',
]
_COMMON_EXPECTED = [
    'communication', 'teamwork', 'problem solving', 'time management',
    'microsoft office', 'leadership', 'project management',
]


def _local_resume_analysis(resume_text, job_description, ats_score=75):
    """Offline skill analysis — no AI call needed."""
    text_low = (resume_text or '').lower()
    jd_low = (job_description or '').lower()

    matching_skills = sorted({
        skill for skill in _TECH_SKILLS
        if re.search(r'\b' + re.escape(skill) + r'\b', text_low)
    })

    if jd_low.strip():
        jd_skills = {
            skill for skill in _TECH_SKILLS
            if re.search(r'\b' + re.escape(skill) + r'\b', jd_low)
        }
        missing_skills = sorted(jd_skills - set(matching_skills))
        analysis = (
            f"Your resume matches {len(matching_skills)} of the required skills. "
            f"Consider adding experience with the {len(missing_skills)} missing skill(s) to improve your chances."
        )
    else:
        missing_skills = sorted({
            skill for skill in _COMMON_EXPECTED
            if not re.search(r'\b' + re.escape(skill) + r'\b', text_low)
        })
        analysis = (
            f"Your resume contains {len(matching_skills)} identifiable professional skill(s). "
            "Add a dedicated Skills section and quantify achievements to improve your ATS score."
        )

    advice = []
    if ats_score < 50:
        advice.append("Add a clear Skills section listing your technical and soft skills.")
        advice.append("Include your email and phone number prominently at the top.")
    if ats_score < 70:
        advice.append("Use strong action verbs (e.g., 'Led', 'Built', 'Improved') to start bullet points.")
        advice.append("Quantify achievements with numbers or percentages where possible.")
    if missing_skills:
        advice.append(f"Consider developing skills in: {', '.join(missing_skills[:5])}.")
    advice.append("Tailor your resume to each job description to maximise keyword matching.")

    return {
        "match_percentage": ats_score,
        "matching_skills": matching_skills if matching_skills else ["No specific skills detected — add a Skills section"],
        "missing_skills": missing_skills if missing_skills else ["No critical gaps detected"],
        "analysis": analysis,
        "career_advice": advice,
    }


def analyze_resume_with_sarvam(resume_text, job_description=""):
    resume_text = str(resume_text or "")[:4000]
    job_description = str(job_description or "")[:2000]
    if not job_description.strip():
        prompt = f"""
You are an expert HR and Technical Recruiter. Analyze the following Resume and provide an ATS (Applicant Tracking System) score and skill extraction.

Resume:
{resume_text}

Provide a detailed analysis in JSON format with these keys:
- "match_percentage": integer 0-100 (This is the ATS Score based on formatting, keyword density, and professional standards)
- "missing_skills": list of strings – skills that are usually expected for this candidate's profile but missing or weak in the resume
- "matching_skills": list of strings – all identifiable professional skills found in the resume
- "analysis": string – brief summary of the resume's strength and overall quality (max 3 sentences)
- "career_advice": list of strings – recommendations to improve the resume or career path

Return ONLY raw JSON. No markdown, no trailing commas.
"""
    else:
        prompt = f"""
You are an expert HR and Technical Recruiter. Analyze the following Resume against the Job Description.

Job Description:
{job_description}

Resume:
{resume_text}

Provide a detailed analysis in JSON format with these keys:
- "match_percentage": integer 0-100
- "missing_skills": list of strings – skills in JD but missing in Resume
- "matching_skills": list of strings – skills present in both
- "analysis": string – brief summary of fit (max 3 sentences)
- "career_advice": list of strings – recommendations to improve

Return ONLY raw JSON. No markdown, no trailing commas.
"""
    try:
        raw = _sarvam_chat(prompt)
        return _parse_json_response(raw)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"AI Analysis failed, using local fallback: {e}")
        return _local_resume_analysis(resume_text, job_description)


def extract_experience_years(text):
    """Tries to find years of experience in the text. Returns float."""
    if not text:
        return 0.0
    text_lower = text.lower()
    # Patterns like "3 years", "2.5 yrs", "5+ years"
    match = re.search(r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:year|yr)', text_lower)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return 0.0


def get_target_difficulties(years):
    """Maps years to a list of matching difficulty strings in DB."""
    if years <= 1:
        return ["Beginner", "Easy", "beginner", "easy"]
    elif years <= 2:
        return ["Intermediate", "Medium", "intermediate", "medium"]
    else:
        return ["Advanced", "Hard", "advanced", "hard"]


def generate_interview_questions(resume_text, job_description, skills=None):
    from core.models import FAQQuestion
    import random
    import logging

    logger = logging.getLogger(__name__)
    
    if not skills:
        skills = []
    
    # 1. Determine Difficulty based on Experience
    years = extract_experience_years(resume_text)
    target_diffs = get_target_difficulties(years)
    logger.info(f"Detected {years} years of experience. Targeting difficulties: {target_diffs}")

    # Normalize skills to lowercase for matching
    normalized_skills = [s.strip().lower() for s in skills if s.strip()]
    
    questions_by_skill = {}
    for skill in normalized_skills:
        # Filter by skill AND difficulty
        qs = list(FAQQuestion.objects.filter(
            topic__iexact=skill,
            difficulty__in=target_diffs
        ))
        
        # Fallback: if no questions for that difficulty, take any for that skill
        if not qs:
            qs = list(FAQQuestion.objects.filter(topic__iexact=skill))
            
        if qs:
            random.shuffle(qs)
            questions_by_skill[skill] = qs
        else:
            logger.warning(f"No questions found for skill: {skill}")

    target_count = 5
    final_questions = []
    
    # Use round-robin to ensure a mix of all skills
    used_texts = set()
    if questions_by_skill:
        while len(final_questions) < target_count and questions_by_skill:
            skills_to_remove = []
            for skill in list(questions_by_skill.keys()):
                if len(final_questions) >= target_count:
                    break
                if questions_by_skill[skill]:
                    q = questions_by_skill[skill].pop()
                    if q.question_text not in used_texts:
                        final_questions.append(q)
                        used_texts.add(q.question_text)
                else:
                    skills_to_remove.append(skill)
            
            for s in skills_to_remove:
                if s in questions_by_skill:
                    del questions_by_skill[s]
    
    # Double shuffle the final list so the topics aren't strictly sequential
    random.shuffle(final_questions)
    
    if not final_questions:
        # Fallback if no skills matched any database questions
        logger.warning("No database questions matched any skills. Falling back to targeted difficulty sample.")
        qs = FAQQuestion.objects.filter(difficulty__in=target_diffs)
        if not qs.exists():
            qs = FAQQuestion.objects.all()
            
        if qs.exists():
            final_questions = random.sample(list(qs), min(target_count, qs.count()))

    # Convert to the format expected by the view
    return [
        {'topic': q.topic.capitalize(), 'question': q.question_text}
        for q in final_questions
    ]


def evaluate_answer(question, answer):
    prompt = f"""
You are an expert technical interviewer. Evaluate the following answer.

Question: {question}
Answer: {answer}

Output JSON with:
- "score": integer 0-10
- "feedback": string (max 2 sentences, constructive)

Return ONLY raw JSON. No markdown.
"""
    try:
        raw = _sarvam_chat(prompt)
        result = _parse_json_response(raw)
        
        # Ensure result is a dict
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
            
        if not isinstance(result, dict):
            result = {}
            
        result.setdefault('score', 0)
        result.setdefault('feedback', 'Could not parse AI response.')
        return result
    except Exception as e:
        return {'score': 0, 'feedback': f'Error: {e}'}

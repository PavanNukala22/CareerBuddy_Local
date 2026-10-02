"""
Utility functions for the Resume Builder feature.
Uses the existing SARVAM_API_KEY from the environment.
"""
import functools
import json
import os
import re
import logging
import requests

logger = logging.getLogger(__name__)


def get_sarvam_api_key():
    try:
        from decouple import config
        return config('SARVAM_API_KEY', default='')
    except Exception:
        return os.environ.get('SARVAM_API_KEY', '')


# --- PDF extraction engines (tried in order until one yields text) -------------

def _extract_with_pypdf_layout(file_path):
    """pypdf v4+ with layout-aware extraction - best for multi-column resumes."""
    import pypdf  # type: ignore
    text_parts = []
    reader = pypdf.PdfReader(file_path)
    for page in reader.pages:
        try:
            # extract_text(extraction_mode="layout") preserves column ordering
            page_text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            # older pypdf that doesn't know extraction_mode
            page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_with_pypdf_plain(file_path):
    """pypdf plain extraction - fast and works for most standard PDFs."""
    import pypdf  # type: ignore
    text_parts = []
    reader = pypdf.PdfReader(file_path)
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_with_pdfplumber(file_path):
    """pdfplumber - excels at template-heavy & table-rich PDFs."""
    import pdfplumber  # type: ignore
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text_parts.append(page_text)
    return "\n".join(text_parts).strip()


def _extract_with_pdfminer(file_path):
    """pdfminer.six - handles complex font encoding where others produce garbage."""
    from pdfminer.high_level import extract_text as pdfminer_extract  # type: ignore
    text = pdfminer_extract(file_path) or ""
    return text.strip()


def _extract_with_pypdf2(file_path):
    """PyPDF2 legacy - last resort for old-format PDFs."""
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
    """
    Try multiple PDF extraction engines in order.  Returns the first
    non-empty result, an error string if every engine raised, or '' when
    all engines succeed but find no text (e.g. a fully scanned/image PDF).
    """
    last_error = None
    for engine in _PDF_ENGINES:
        try:
            text = engine(file_path)
            if text and len(text.strip()) > 30:   # at least a few meaningful chars
                logger.info(f"PDF extracted via {engine.__name__}, length={len(text)}")
                return text
        except Exception as exc:
            last_error = exc
            logger.warning(f"PDF engine {engine.__name__} failed: {exc}")

    if last_error is not None:
        logger.error(f"All PDF engines failed: {last_error}")
        return f'Error reading PDF: {last_error}'

    # All ran but returned nothing → scanned / image-only PDF
    logger.error("PDF has no extractable text (likely a scanned/image file).")
    return ''


def extract_text_from_docx(file_path):
    """Extract all text from a DOCX including table cells."""
    try:
        import docx  # type: ignore
        doc = docx.Document(file_path)
        parts = []
        # Body paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        # Tables (many resume templates put skills/contact in tables)
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


def extract_text_from_doc(file_path):
    """Extract text from a legacy Word 97-2003 .doc (binary, OLE container).

    Reads the document's piece table instead of decoding raw bytes, so only the
    real document text comes back — decoding the whole file used to feed
    embedded-object/theme binary garbage into skill and theme matching.
    """
    import struct
    try:
        import olefile
        with olefile.OleFileIO(file_path) as ole:
            word = ole.openstream('WordDocument').read()
            if struct.unpack_from('<H', word, 0)[0] != 0xA5EC:
                return 'Error reading DOC: not a Word 97-2003 document'
            flags = struct.unpack_from('<H', word, 0x0A)[0]
            if flags & 0x0100:  # fEncrypted
                return 'Error reading DOC: document is password-protected'
            table_name = '1Table' if flags & 0x0200 else '0Table'
            table = ole.openstream(table_name).read()

        fc_clx, lcb_clx = struct.unpack_from('<II', word, 0x01A2)
        clx = table[fc_clx:fc_clx + lcb_clx]

        # Skip any Prc (formatting) blocks to reach the Pcdt (piece table).
        pos = 0
        while pos < len(clx) and clx[pos] == 0x01:
            pos += 3 + struct.unpack_from('<H', clx, pos + 1)[0]
        if pos >= len(clx) or clx[pos] != 0x02:
            return 'Error reading DOC: piece table not found'
        lcb = struct.unpack_from('<I', clx, pos + 1)[0]
        plc = clx[pos + 5:pos + 5 + lcb]
        n = (lcb - 4) // 12
        cps = struct.unpack_from(f'<{n + 1}I', plc, 0)

        parts = []
        for i in range(n):
            fc = struct.unpack_from('<I', plc, (n + 1) * 4 + i * 8 + 2)[0]
            length = cps[i + 1] - cps[i]
            if fc & 0x40000000:  # 8-bit (cp1252) piece
                start = (fc & ~0x40000000) // 2
                parts.append(word[start:start + length].decode('cp1252', errors='replace'))
            else:  # UTF-16LE piece
                parts.append(word[fc:fc + 2 * length].decode('utf-16-le', errors='replace'))
        text = ''.join(parts)

        # Drop field instructions (\x13 code \x14 result \x15 -> result) and
        # turn Word's control characters into plain whitespace.
        text = re.sub(r'\x13[^\x13\x14\x15]*\x14', '', text)
        text = re.sub(r'\x13[^\x13\x14\x15]*\x15', '', text)
        text = text.translate({0x15: None, 0x07: '\t', 0x0B: '\n', 0x0C: '\n', 0x0D: '\n',
                               0x1E: '-', 0x1F: None, 0xA0: ' '})
        text = re.sub(r'[\x00-\x08\x0e-\x1d]', '', text)
        return re.sub(r'\n{3,}', '\n\n', text).strip()
    except Exception as e:
        logger.error(f"DOC extraction failed: {e}")
        return f'Error reading DOC: {e}'



def _sarvam_chat(prompt, temperature=0.7, timeout=45, max_retries=3):
    """Send a prompt to Sarvam AI chat completions and return the raw text.
    Retries up to 3 times with exponential backoff on timeout/connection errors.
    """
    import time
    import logging
    from django.conf import settings
    _logger = logging.getLogger(__name__)
    api_key = get_sarvam_api_key()
    if not api_key:
        raise ValueError('SARVAM_API_KEY is missing.')
    headers = {
        'api-subscription-key': api_key,
        'Content-Type': 'application/json',
    }
    model = getattr(settings, 'SARVAM_MODEL', 'sarvam-105b')
    data = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant.'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': temperature,
        'reasoning_effort': None,
    }

    # 10s was too tight for normal LLM response latency on a live server —
    # this call was timing out on responses that just needed a bit longer,
    # not on actual outages (a real outage/rate-limit fails fast with a
    # connection error or 429, not a slow-but-eventually-complete response).
    # 45s matches the timeout used for the equivalent Sarvam chat call in
    # activities/agents/utils.py. max_retries was also silently 1 despite
    # this docstring promising 3 retries with backoff — a single slow
    # response failed the whole evaluation immediately with no actual retry.
    max_retries = max(1, max_retries)
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                'https://api.sarvam.ai/v1/chat/completions',
                headers=headers, json=data, timeout=timeout,
            )
            _logger.info(f"Sarvam API Response Status: {response.status_code}")
            _logger.debug(f"Sarvam API Response Body: {response.text}")
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            _logger.warning(f"Sarvam API attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                time.sleep(1.5 * attempt)
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


ATS_SECTION_KEYWORDS = {
    'summary': ['summary', 'objective', 'profile', 'about me'],
    'experience': ['experience', 'work history', 'employment', 'professional experience', 'work experience'],
    'education': ['education', 'academic', 'qualification', 'degree', 'university', 'college'],
    'skills': ['skills', 'technical skills', 'competencies', 'expertise', 'proficiencies'],
    'projects': ['project', 'projects'],
    'certifications': ['certification', 'certificate', 'certified'],
}

ATS_ACTION_VERBS = [
    'managed', 'developed', 'led', 'created', 'designed', 'implemented', 'built',
    'improved', 'achieved', 'delivered', 'analyzed', 'coordinated', 'launched',
    'increased', 'reduced', 'optimized', 'maintained', 'collaborated', 'handled',
    'supported', 'trained', 'resolved', 'executed', 'automated', 'streamlined',
]

_ATS_STOPWORDS = {
    'and', 'the', 'for', 'with', 'you', 'are', 'will', 'our', 'have', 'this',
    'that', 'who', 'from', 'your', 'their', 'has', 'was', 'must', 'should',
    'able', 'work', 'role', 'team', 'good', 'strong', 'ability', 'years',
}


def compute_ats_score(resume_text, job_description=""):
    """
    Deterministic, rule-based ATS score (0-100). The SAME resume always
    produces the SAME score — no AI randomness. Weights sum to 100.
    """
    text = resume_text or ""
    low = text.lower()
    words = re.findall(r'[a-zA-Z]+', low)
    wc = len(words)
    if wc == 0:
        return 0

    score = 0.0

    # 1. Contact info (15)
    phone_match = re.search(r'(\+?\d[\d\-\s()]{7,}\d)', text)
    if re.search(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', low):
        score += 8
    if phone_match:
        score += 7

    # 2. Core sections (28): summary, experience, education, skills — 7 each
    for sec in ('summary', 'experience', 'education', 'skills'):
        if any(kw in low for kw in ATS_SECTION_KEYWORDS[sec]):
            score += 7

    # 3. Bonus sections (6): projects, certifications — 3 each
    for sec in ('projects', 'certifications'):
        if any(kw in low for kw in ATS_SECTION_KEYWORDS[sec]):
            score += 3

    # 4. Action verbs (12): 1 point each, capped at 12
    verbs_found = sum(1 for v in ATS_ACTION_VERBS if re.search(r'\b' + v + r'\b', low))
    score += min(verbs_found, 12)

    # 5. Quantified achievements (10): numbers / percentages
    # The phone number counted under Contact info is a digit run too, and a
    # calendar year counted under Dates below is just as much a "\d{2,}" as a
    # real metric — neither belongs here twice, so both are excluded before
    # counting, rather than letting a phone number or a work-history date
    # inflate a score meant for actual measured achievements.
    quant_source = text
    if phone_match:
        quant_source = text[:phone_match.start(1)] + text[phone_match.end(1):]
    quant_matches = re.findall(r'\b\d+%|\b\d{2,}\b', quant_source)
    quant = sum(1 for m in quant_matches if not re.fullmatch(r'(?:19|20)\d{2}', m))
    score += min(quant * 2, 10)

    # 6. Length adequacy (9): ~200-900 words is ideal
    if 200 <= wc <= 900:
        score += 9
    elif 120 <= wc < 200 or 900 < wc <= 1200:
        score += 6
    elif wc >= 60:
        score += 3

    # 7. Dates / timeline (5): year patterns
    year_hits = len(re.findall(r'\b(?:19|20)\d{2}\b', text))
    score += 5 if year_hits >= 2 else (2 if year_hits == 1 else 0)

    # 8. Keyword match (15): against a job description, else skills-density proxy
    if str(job_description or "").strip():
        jd_low = job_description.lower()
        jd_keywords = {
            k for k in re.findall(r'[a-zA-Z][a-zA-Z+#.]{3,}', jd_low)
            if k not in _ATS_STOPWORDS
        }
        if jd_keywords:
            matched = sum(1 for k in jd_keywords if k in low)
            score += round((matched / len(jd_keywords)) * 15)
    else:
        unique = len(set(words))
        if unique >= 200:
            score += 15
        elif unique >= 120:
            score += 11
        elif unique >= 70:
            score += 7
        elif unique >= 40:
            score += 4

    return round(min(max(score, 0.0), 100.0))


# ─── Comprehensive skill vocabulary for local (offline) analysis ───────────────
_TECH_SKILLS = [
    # Programming languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php',
    'swift', 'kotlin', 'go', 'rust', 'scala', 'r', 'matlab', 'perl', 'bash',
    'shell', 'powershell', 'vba', 'dart', 'lua',
    # Web / Frontend
    'html', 'css', 'react', 'angular', 'vue', 'jquery', 'bootstrap', 'tailwind',
    'sass', 'webpack', 'node.js', 'nodejs', 'express', 'django', 'flask',
    'fastapi', 'spring', 'laravel', 'rails', 'asp.net', 'next.js', 'nuxt',
    # Data & ML
    'machine learning', 'deep learning', 'nlp', 'natural language processing',
    'computer vision', 'tensorflow', 'pytorch', 'keras', 'scikit-learn',
    'pandas', 'numpy', 'matplotlib', 'seaborn', 'spark', 'hadoop',
    'data analysis', 'data science', 'data engineering', 'etl',
    'power bi', 'tableau', 'looker', 'excel', 'statistics',
    # Cloud & DevOps
    'aws', 'azure', 'gcp', 'google cloud', 'docker', 'kubernetes', 'terraform',
    'ansible', 'jenkins', 'ci/cd', 'devops', 'linux', 'unix', 'nginx', 'apache',
    'microservices', 'serverless', 'git', 'github', 'gitlab', 'bitbucket',
    # Databases
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
    'oracle', 'sqlite', 'dynamodb', 'cassandra', 'firebase',
    # Mobile
    'android', 'ios', 'react native', 'flutter', 'xamarin',
    # PM / Tools
    'agile', 'scrum', 'kanban', 'jira', 'confluence', 'trello', 'asana',
    'project management', 'product management', 'product owner',
    # Networking / Security
    'networking', 'tcp/ip', 'rest api', 'graphql', 'microservices',
    'cybersecurity', 'penetration testing', 'siem', 'firewall',
    # Office / Business
    'microsoft office', 'google workspace', 'crm', 'salesforce', 'sap', 'erp',
    'business analysis', 'business intelligence', 'financial analysis',
    'accounting', 'supply chain', 'logistics',
    # Soft skills
    'leadership', 'communication', 'teamwork', 'problem solving',
    'critical thinking', 'time management', 'adaptability', 'creativity',
    'collaboration', 'presentation', 'negotiation', 'mentoring', 'coaching',
    'customer service', 'stakeholder management', 'cross-functional',
    # Core-engineering / mechanical / civil skills so non-IT technical resumes
    # surface real skills instead of only generic soft skills.
    'autocad', 'solidworks', 'catia', 'creo', 'ansys', 'nx', 'revit', 'staad',
    'staad pro', 'etabs', 'primavera', 'ms project', 'cad', 'cam', 'cnc',
    'gd&t', 'welding', 'fabrication', 'machining', 'casting', 'molding',
    'thermodynamics', 'fluid mechanics', 'hvac', 'pneumatics', 'hydraulics',
    'plc', 'scada', 'six sigma', 'lean manufacturing', 'quality control',
    'quality assurance', 'qa/qc', 'iso 9001', 'ndt', 'prototyping', 'tooling',
    'sheet metal', 'surveying', 'estimation', 'structural analysis',
    'concrete technology', 'geotechnical', 'construction management',
    'site supervision', 'site engineering', 'bill of materials', 'bom',
]

# Common skills expected in most professional roles
_COMMON_EXPECTED = [
    'communication', 'teamwork', 'problem solving', 'time management',
    'microsoft office', 'leadership', 'project management',
]


def _local_resume_analysis(resume_text, job_description, ats_score):
    """
    Offline, zero-dependency skill analysis.
    Scans resume text against a vocabulary of 100+ skills to build
    real matching_skills and missing_skills lists — no AI call needed.
    """
    text_low = (resume_text or '').lower()
    jd_low = (job_description or '').lower()

    # Skills actually found in the resume
    matching_skills = sorted({
        skill for skill in _TECH_SKILLS
        if re.search(r'\b' + re.escape(skill) + r'\b', text_low)
    })

    if jd_low.strip():
        # Missing = skills mentioned in JD but not in resume
        jd_skills = {
            skill for skill in _TECH_SKILLS
            if re.search(r'\b' + re.escape(skill) + r'\b', jd_low)
        }
        missing_skills = sorted(jd_skills - set(matching_skills))
        analysis = (
            f"Your resume matches {len(matching_skills)} of the required skills. "
            f"Consider adding experience with the {len(missing_skills)} missing skill(s) "
            "to improve your chances."
        )
    else:
        # Missing = common expected skills not found in resume
        missing_skills = sorted({
            skill for skill in _COMMON_EXPECTED
            if not re.search(r'\b' + re.escape(skill) + r'\b', text_low)
        })
        analysis = (
            f"Your resume contains {len(matching_skills)} identifiable professional skill(s). "
            "Add a dedicated Skills section and quantify achievements to improve your ATS score."
        )

    # Build context-aware career advice
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
- "missing_skills": list of strings - skills that are usually expected for this candidate's profile but missing or weak in the resume
- "matching_skills": list of strings - all identifiable professional skills found in the resume
- "analysis": string - brief summary of the resume's strength and overall quality (max 3 sentences)
- "career_advice": list of strings - recommendations to improve the resume or career path

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
- "missing_skills": list of strings - skills in JD but missing in Resume
- "matching_skills": list of strings - skills present in both
- "analysis": string - brief summary of fit (max 3 sentences)
- "career_advice": list of strings - recommendations to improve

Return ONLY raw JSON. No markdown, no trailing commas.
"""
    # Deterministic ATS score — same resume always gets the same fair score.
    # The local analysis (score + real matching/missing skills from the resume
    # text) is always computed so it can backfill any field the model leaves
    # blank — that is what guarantees the page shows the ATS score, matching
    # skills and missing skills every time, instead of a blank 0% / "No exact
    # matches" whenever the model returns empty or malformed JSON.
    ats_score = compute_ats_score(resume_text, job_description)
    local = _local_resume_analysis(resume_text, job_description, ats_score)
    try:
        # temperature=0 keeps the qualitative analysis stable too
        raw = _sarvam_chat(prompt, temperature=0)
        result = _parse_json_response(raw)
        # The model sometimes wraps the object in a single-item list.
        if isinstance(result, list) and result and isinstance(result[0], dict):
            result = result[0]
        if not isinstance(result, dict) or not result:
            return local
        # Override the AI's variable number with our consistent score, and
        # backfill any empty field from the deterministic local analysis.
        result['match_percentage'] = ats_score
        for key in ('matching_skills', 'missing_skills', 'analysis', 'career_advice'):
            if not result.get(key):
                result[key] = local[key]
        return result
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"AI Analysis failed, using local fallback: {e}")
        return local


def extract_experience_years(text):
    """Years of professional experience from the resume. Returns float.

    Prefers a year-count that sits next to the word "experience" (e.g.
    "12+ years of experience", "experience: 8 years") over any stray "N years"
    in the text — a graduation gap, an age, or a project duration used to
    inflate the number and push a mid-level candidate to Expert difficulty.
    Values above 50 are treated as noise. Falls back to the first plausible
    "N years" only when no experience-anchored figure is found.
    """
    if not text:
        return 0.0
    low = text.lower()
    year_re = r'(\d{1,2}(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)'

    # 1. Prefer a figure within ~45 chars of the word "experience".
    best = 0.0
    for m in re.finditer(year_re, low):
        try:
            val = float(m.group(1))
        except ValueError:
            continue
        if val > 50:
            continue
        ctx = low[max(0, m.start() - 45):min(len(low), m.end() + 45)]
        if 'experience' in ctx or 'exp.' in ctx:
            best = max(best, val)
    if best:
        return best

    # 2. Fallback: first plausible "N years" anywhere.
    m = re.search(year_re, low)
    if m:
        try:
            val = float(m.group(1))
            return val if val <= 50 else 0.0
        except ValueError:
            pass
    return 0.0


# ── Experience-level classification ──────────────────────────────────────────
#
# Previously years-of-experience only shifted the domain question difficulty
# MIX (e.g. mostly Easy for <=2 years) - but that mix always included at
# least one Hard question, even for a true 0-year fresher. There was also no
# explicit experience-level label stored anywhere, just a raw years float.
# This gives each interview a real classification (matching the spec's exact
# bands) and a hard floor/ceiling on difficulty for that level, so a fresher
# can never be handed an Expert-level question no matter how the adaptive
# step would otherwise nudge it, and a Senior/Expert candidate never gets
# stuck on Easy questions either.

EXPERIENCE_LEVELS = [
    ('fresher', 'Fresher', 0, 0),
    ('entry_level', 'Entry Level', 0, 1),
    ('junior', 'Junior', 1, 3),
    ('mid_level', 'Mid Level', 3, 5),
    ('senior', 'Senior', 5, 8),
    ('expert', 'Expert', 8, None),
]

# (starting_difficulty, min_difficulty, max_difficulty) per level - all
# within this project's existing Easy/Intermediate/Hard scale.
_EXPERIENCE_DIFFICULTY_BOUNDS = {
    'fresher':     ('Easy',         'Easy',         'Intermediate'),
    'entry_level': ('Easy',         'Easy',         'Intermediate'),
    'junior':      ('Easy',         'Easy',         'Hard'),
    'mid_level':   ('Intermediate', 'Easy',         'Hard'),
    'senior':      ('Intermediate', 'Intermediate', 'Hard'),
    'expert':      ('Hard',         'Intermediate', 'Hard'),
}


def classify_experience_level(years):
    """Map raw years-of-experience to one of the spec's six experience
    bands. Returns the internal key (e.g. 'mid_level'); see
    EXPERIENCE_LEVELS for the matching display label."""
    try:
        years = float(years)
    except (TypeError, ValueError):
        years = 0.0
    if years <= 0:
        return 'fresher'
    elif years <= 1:
        return 'entry_level'
    elif years <= 3:
        return 'junior'
    elif years <= 5:
        return 'mid_level'
    elif years <= 8:
        return 'senior'
    return 'expert'


def experience_level_label(level_key):
    for key, label, _lo, _hi in EXPERIENCE_LEVELS:
        if key == level_key:
            return label
    return 'Fresher'


def get_target_difficulties(years):
    """Maps years to a list of matching difficulty strings in DB."""
    if years <= 1:
        return ["Beginner", "Easy", "beginner", "easy"]
    elif years <= 2:
        return ["Intermediate", "Medium", "intermediate", "medium"]
    else:
        return ["Advanced", "Hard", "advanced", "hard"]


PROCESS_TOPICS = [
    "customer support", "technical support", "sales", "appointment setting",
    "email support", "chat support", "back office", "data processing", "hr shared services",
    "it help desk analyst", "service desk analyst", "desktop support engineer",
    "application support engineer", "customer technical support specialist",
    "network support engineer", "cloud support associate", "gis executive",
    "aml/kyc executive", "content moderator"
]

# Topics in FAQQuestion that hold the HR-style banks rather than domain content.
# They are seeded from the lists below by `manage.py import_question_bank`.
BEHAVIOURAL_TOPIC = 'behavioural'
EXPERIENCE_TOPIC = 'experience'
# Q6-10 for a Fresher/Entry-Level candidate (see classify_experience_level) —
# a candidate with no professional employment has nothing an "experience"
# question can honestly be about, so this bank asks about academics/projects/
# internships/coursework instead of assuming a past job existed.
ACADEMIC_TOPIC = 'academic_project'
BANK_TOPICS = (BEHAVIOURAL_TOPIC, EXPERIENCE_TOPIC, ACADEMIC_TOPIC)

# Difficulty labels actually present across the 4 CSV question banks in data/.
# interview_questions.csv uses Beginner/Intermediate/Advanced (IT/technical
# topics); non_voice_process.csv, voice_process.csv and
# technical_support_engineering.csv use experience-year buckets instead
# (Fresher, 1-3 Years, 3-5 Years, 5+ Years) since they're organized by
# candidate seniority rather than concept difficulty. Both column styles are
# mapped onto this project's Easy/Intermediate/Hard scale here, in the one
# place both generate_interview_questions() and select_next_domain_question()
# read from — previously only the Beginner/Advanced style was mapped, so every
# row from the other 3 CSVs (the ones a Non-IT candidate's questions actually
# come from) silently fell outside every difficulty tier and was only ever
# reached through the untiered fallback, making difficulty effectively random
# for Non-IT candidates regardless of their real experience level.
DIFFICULTY_DB_KEYS = {
    'Easy': ['Beginner', 'Easy', 'beginner', 'easy', 'Fresher', 'fresher'],
    'Intermediate': [
        'Intermediate', 'Medium', 'intermediate', 'medium',
        '1-3 Years', '1-3 Years Experience',
    ],
    'Hard': [
        'Advanced', 'Hard', 'advanced', 'hard',
        '3-5 Years', '3-5 Years Experience', '5+ Years', '5+ Years Experience',
    ],
}

# Filler words inside compound topic names. `_matching_bank_topics` splits a
# topic like "docker & containers" on its separators and matches the parts, so
# these are excluded to stop a topic matching on a word every resume contains.
TOPIC_STOPWORDS = frozenset({
    'and', 'the', 'other', 'others', 'general', 'basics', 'basic', 'advanced',
    'intro', 'introduction', 'misc', 'miscellaneous', 'concepts', 'fundamentals',
    'tools', 'topics', 'management', 'process', 'processes', 'support',
    'services', 'systems', 'technology', 'staffing', 'control', 'design',
})

# Seed data for the DB banks above; also used as a last-resort fallback if the
# import command has never been run.
BEHAVIOURAL_QUESTIONS = [
    "Tell me about yourself and what motivates you professionally.",
    "Describe a time you had a conflict with a coworker and how you resolved it.",
    "What are your greatest strengths, and how do they help you at work?",
    "Tell me about a mistake you made and what you learned from it.",
    "How do you handle pressure or tight deadlines?",
    "Describe a situation where you demonstrated leadership.",
    "How do you prioritise your work when handling multiple tasks?",
    "Where do you see yourself in the next five years?",
    "Tell me about a time you received difficult feedback and how you responded.",
    "How do you handle disagreements with your manager or team?",
]

EXPERIENCE_QUESTIONS = [
    "Walk me through your most significant project and your exact role in it.",
    "What has been your biggest professional achievement so far?",
    "Describe a challenging problem you solved in a previous role.",
    "Which tools or technologies have you used most in your work, and why?",
    "Tell me about a project that did not go as planned and how you handled it.",
    "How has your past experience prepared you for this role?",
    "Describe a time you had to learn a new skill quickly for a project.",
    "What was your contribution to your team's success in your last role?",
    "Tell me about a time you improved a process or system at work.",
    "Describe the work environment in which you perform your best.",
]

# Q6-10 for Fresher/Entry-Level candidates (0-1 year of professional
# experience — see classify_experience_level) in place of EXPERIENCE_QUESTIONS
# above, which presumes a past job. These ask about academics, final-year/
# personal projects, internships, coursework and certifications instead —
# grounded in what a fresher's resume actually contains, without presuming or
# fabricating any specific project/technology the candidate hasn't mentioned.
ACADEMIC_PROJECT_QUESTIONS = [
    "Walk me through your final-year or most significant academic project, including your specific role.",
    "Describe a personal or academic project you're proud of and why you chose that approach.",
    "What was the most challenging concept or assignment you worked through during your studies, and how did you approach it?",
    "Tell me about an internship or practical training experience and what you learned from it.",
    "Which subjects, courses or certifications have been most relevant to the role you're applying for?",
    "Describe a time you worked in a group project — what was your contribution and how did the team divide the work?",
    "Tell me about a project where you had to learn a new tool or concept from scratch to complete it.",
    "What project or assignment took the most effort to get right, and what would you do differently now?",
    "How did you decide on the topic or approach for your major academic project?",
    "Describe a time a project or assignment didn't go as planned and how you handled it.",
]


def classify_candidate_type(resume_text, skills=None, years=None):
    """Classify a candidate into one of the four types the interview module
    is calibrated for: IT_EXPERIENCED, IT_FRESHER, NON_IT_EXPERIENCED,
    NON_IT_FRESHER.

    IT/Non-IT comes from _is_it_profile (resume + skills content). Fresher vs
    Experienced reuses classify_experience_level's existing 1-year boundary
    (fresher/entry_level = 0-1yr = Fresher; junior and above = >1yr =
    Experienced) rather than inventing a second threshold, so this always
    agrees with the difficulty calibration already driven by that function.
    Pass `years` if already computed by the caller to avoid re-parsing the
    resume text for experience years.
    """
    skills = skills or []
    is_it = _is_it_profile(resume_text, skills)
    if years is None:
        years = extract_experience_years(resume_text)
    is_experienced = classify_experience_level(years) not in ('fresher', 'entry_level')
    if is_it:
        return 'IT_EXPERIENCED' if is_experienced else 'IT_FRESHER'
    return 'NON_IT_EXPERIENCED' if is_experienced else 'NON_IT_FRESHER'

# Keywords that indicate a software/IT/coding profile. Used to decide whether the
# "technical" questions (Q11-20) should be coding-oriented or domain-oriented.
IT_KEYWORDS = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue", "node",
    "django", "flask", "spring", ".net", "c#", "c++", "golang", "php", "ruby", "kotlin",
    "swift", "android", "ios", "html", "css", "sql", "mongodb", "postgres", "mysql",
    "redis", "aws", "azure", "gcp", "docker", "kubernetes", "devops", "linux", "git",
    "api", "rest", "microservice", "backend", "frontend", "full stack", "fullstack",
    "software", "developer", "programming", "coding", "machine learning", "data science",
    "tensorflow", "pytorch", "selenium", "cloud", "software engineer",
    # Cybersecurity / IT-infra: a security or infra profile is IT, but its
    # vocabulary (SIEM, SOC, pentest, firewalls) shares no word with the
    # software list above, so without these it classified as NON-IT and lost its
    # own 'data, cloud & cybersecurity' industry to oil&gas / data-centre noise.
    "cybersecurity", "cyber security", "information security", "network security",
    "siem", "splunk", "soc analyst", "penetration testing", "pentest",
    "ethical hacking", "vulnerability", "malware", "incident response",
    "firewall", "wireshark", "nessus", "endpoint security", "active directory",
]


def _term_in_text(term, haystack):
    """Word-boundary-aware substring check: does `term` appear in `haystack`
    as a whole word, not merely as a run of letters inside a longer word?

    Plain `term in haystack` false-positives badly for short alphanumeric
    keywords — e.g. the IT keyword "git" matches inside "di-GIT-al" (as in
    "digital marketing"), and "api" matches inside "r-API-d" — so a Non-IT
    marketing resume containing "Digital Marketing" was previously
    classified as an IT profile purely because "git" is a substring of
    "digital". Word-boundary matching (\\bgit\\b) requires "git" to be its
    own token, not a substring, which "digital" never satisfies.

    Terms with no usable word boundary on both ends (c++, c#) fall back to a
    plain substring check, same as `_matching_bank_topics._mentions` does.
    """
    term = (term or "").strip()
    if not term:
        return False
    if re.search(r"\w$", term) and re.search(r"^\w", term):
        return bool(re.search(r"\b" + re.escape(term) + r"\b", haystack))
    return term in haystack


# IT keywords that are too generic to imply an IT profile on their own — a
# Mechanical or Civil engineer's resume routinely says "software & tools" (CAD),
# "cloud", "data" or "api" without being a software candidate. These only count
# toward an IT classification in combination.
# Keywords that alone do NOT make a resume an IT profile. Beyond the generic
# words, this covers the data/office tools that sit on plenty of non-IT
# resumes — a BBA, HR, marketing or accounts candidate listing "SQL" or
# "HTML" is not a software engineer, and treating SQL as a strong signal
# flipped those resumes to IT and served them SQL/Python questions. Two or
# more of these together (e.g. sql + mongodb) still classify as IT.
_WEAK_IT_KEYWORDS = frozenset({
    'software', 'cloud', 'api', 'rest', 'linux', 'data',
    'sql', 'mysql', 'postgres', 'mongodb', 'html', 'css',
})


def _is_it_profile(resume_text, skills):
    """True if the resume/skills look like a software/IT/coding profile.

    Requires either one DISTINCTIVE IT keyword (a language/framework/tool like
    python, django, kubernetes) or at least two keywords total. A single generic
    word such as "software" no longer flips a non-IT resume to IT.
    """
    blob = ((resume_text or "") + " " + " ".join(skills or [])).lower()
    hits = [k for k in IT_KEYWORDS if _term_in_text(k, blob)]
    strong = [k for k in hits if k not in _WEAK_IT_KEYWORDS]
    return len(strong) >= 1 or len(hits) >= 2


# Non-IT "technical"/domain fallback questions, used when the candidate is NOT from
# an IT background and the question bank lacks domain-specific items.
NON_IT_TECHNICAL_FALLBACK = [
    "Explain the key processes and best practices in your field of work.",
    "What tools or software are commonly used in your domain, and how have you used them?",
    "How do you ensure quality and accuracy in your day-to-day work?",
    "Which industry regulations, standards or compliance rules are relevant to your role?",
    "How do you handle a high-volume workload while maintaining accuracy?",
    "Describe a domain-specific problem you solved and the approach you took.",
    "What key metrics or KPIs matter most in your role, and how do you track them?",
    "How do you stay updated with changes and trends in your industry?",
    "Walk me through a typical workflow or procedure you follow in your job.",
    "What are the biggest challenges in your field, and how do you address them?",
]

# IT/software "technical"/domain fallback questions. The FAQQuestion bank's
# ~10k domain rows are loaded by a one-off `manage.py import_question_bank`
# data-import command, not a migration — an environment where that command
# was never run (or the DB was reset without re-running it) has zero domain
# rows. Non-IT candidates already had NON_IT_TECHNICAL_FALLBACK covering that
# case; IT candidates had no equivalent safety net, so Q11-20 silently
# produced 0 questions there, leaving only the 5 Behavioural + 5 Experience
# questions (which do have in-code fallbacks) — a 10-question interview
# instead of 20. This guarantees the technical section the same way.
IT_TECHNICAL_FALLBACK = [
    "Walk me through how you would design and structure a new feature from requirements to deployment.",
    "How do you approach debugging an issue you can't immediately reproduce?",
    "Explain the difference between a process and a thread, and when each matters.",
    "How do you decide between building something in-house versus using an existing library or service?",
    "Describe your approach to writing tests for a piece of code you've built.",
    "What steps do you take to review someone else's code, and what do you look for?",
    "How do you handle a production issue that needs an urgent fix?",
    "Explain how you would optimize a slow-performing piece of code or query.",
    "What version control practices do you follow when working with a team?",
    "How do you keep your technical skills up to date with new tools and practices?",
    "Describe a time you had to learn a new technology quickly to finish a project.",
    "How do you approach securing an application against common vulnerabilities?",
]

# ── Semantic near-duplicate detection ───────────────────────────────────────
#
# The question bank has ~6,935 rows but only (topic, difficulty, text) —
# no IDs, no canonical question family. Two questions with the same core
# meaning but different wording ("Explain what a REST API is." vs "What is
# REST API and how does it work?") were previously treated as completely
# unrelated, because every duplicate check in this file compared raw text
# equality only. No embedding infrastructure exists in this project, so this
# uses the fallback the spec explicitly allows: normalized text + keyword
# overlap. DUPLICATE_THRESHOLD is the single place to tune strictness.

DUPLICATE_THRESHOLD = 0.7  # 0.0-1.0. Higher = stricter (fewer questions flagged as duplicates).

_QUESTION_STOPWORDS = {
    'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'what', 'how', 'why', 'when', 'where', 'who', 'which', 'do', 'does', 'did',
    'explain', 'describe', 'define', 'definition', 'tell', 'discuss',
    'of', 'in', 'to', 'and', 'or', 'for', 'with', 'on', 'at', 'by', 'from',
    'your', 'you', 'me', 'about', 'can', 'could', 'would', 'will', 'shall',
    'this', 'that', 'these', 'those', 'it', 'its',
}

# A handful of common technical-interview synonym pairs, so "database
# indexing" and "index in SQL" are recognized as the same concept without
# needing full embeddings. Deliberately small and scoped to this domain
# rather than a general English synonym dictionary.
_TECH_SYNONYMS = {
    'sql': 'database', 'db': 'database', 'databases': 'database',
    'apis': 'api', 'endpoint': 'api', 'endpoints': 'api',
    'oop': 'objectoriented', 'oops': 'objectoriented',
}


def _stem(word):
    """Strip a common suffix so word-form variants ('indexing' / 'index',
    'inheritance' / 'inherited') collapse to roughly the same root. This is
    a lightweight heuristic, not a real stemmer, but it's enough to catch
    the rephrasing patterns that mattered in testing."""
    for suffix in ('ational', 'ization', 'fulness', 'iveness', 'ousness',
                   'ing', 'tion', 'sion', 'ment', 'ness', 'able', 'ible',
                   'ally', 'edly', 'ed', 'es', 'ly', 's'):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]
    return word


# Cached: duplicate checks compare every candidate question against every
# question seen this interview and in past interviews, so the same texts were
# re-normalized thousands of times per interview without it.
@functools.lru_cache(maxsize=50000)
def _normalize_question_text(text):
    text = (text or '').lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


@functools.lru_cache(maxsize=50000)
def _question_keywords(text):
    """The meaningful (non-stopword, len>2) stemmed/synonym-normalized words
    in a question - a cheap proxy for its core topic/concept."""
    words = [
        w for w in _normalize_question_text(text).split()
        if w not in _QUESTION_STOPWORDS and len(w) > 2
    ]
    return frozenset(_TECH_SYNONYMS.get(_stem(w), _stem(w)) for w in words)


def _question_similarity(text_a, text_b):
    """Blended keyword-overlap similarity, 0.0-1.0.

    Plain Jaccard (intersection / union) under-scores a short question
    fully contained in a longer, more elaborate rephrasing of it - e.g.
    "What is polymorphism?" vs "Explain polymorphism in OOP." only scores
    0.5 on Jaccard even though the shorter question's entire content is
    covered by the longer one. Blending in the overlap coefficient
    (intersection / smaller set) fixes that specific case, but the overlap
    coefficient alone is too easily fooled by very short questions sharing
    one keyword ("What is Python?" vs "What is Python used for in data
    science?" would score a false 1.0). Averaging the two catches genuine
    rephrased duplicates while still telling a real follow-up apart from a
    duplicate - verified against both cases below.
    """
    if _normalize_question_text(text_a) == _normalize_question_text(text_b):
        return 1.0

    kw_a, kw_b = _question_keywords(text_a), _question_keywords(text_b)
    if not kw_a or not kw_b:
        return 0.0

    intersection = len(kw_a & kw_b)
    if intersection == 0:
        return 0.0

    union = len(kw_a | kw_b)
    jaccard = intersection / union
    overlap_coefficient = intersection / min(len(kw_a), len(kw_b))
    return (jaccard + overlap_coefficient) / 2


def _is_semantic_duplicate(candidate_text, existing_texts):
    """True if candidate_text is a near-duplicate of anything in existing_texts."""
    for existing in existing_texts:
        if _question_similarity(candidate_text, existing) >= DUPLICATE_THRESHOLD:
            return True
    return False


def _previously_asked_texts(user):
    """Every question this candidate has already been served in past interviews."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return set()
    try:
        from career_app.models import ResumeQuestion
        return set(
            ResumeQuestion.objects.filter(session__resume__user=user)
            .values_list('question_text', flat=True)
        )
    except Exception:
        return set()


# Resume "skills" that are not a subject a domain question can be about.
_SOFT_SKILLS = frozenset({
    'leadership', 'communication', 'teamwork', 'problem solving', 'critical thinking',
    'time management', 'adaptability', 'creativity', 'collaboration', 'presentation',
    'negotiation', 'mentoring', 'coaching', 'customer service', 'stakeholder management',
    'cross-functional', 'microsoft office', 'google workspace',
})


_BANK_INDEX = {'built_at': None, 'data': None}
_BANK_INDEX_TTL_SECONDS = 600


def _domain_bank_index():
    """(rows, tokens, by_industry) over the domain question bank, kept in memory:
    rows = {id: (topic, industry, question)} lower-cased, tokens = {word: ids},
    by_industry = {industry: ids}. Searching ~40k questions for each resume
    skill with SQL LIKE took ~1.5s per interview; this makes it a set lookup.
    Rebuilt every few minutes so newly imported questions are picked up."""
    import time
    from career_app.models import FAQQuestion

    now = time.monotonic()
    # `built_at` None means "never built, or deliberately invalidated" — both
    # must rebuild rather than raise on the subtraction.
    if (_BANK_INDEX['data'] is not None
            and _BANK_INDEX['built_at'] is not None
            and now - _BANK_INDEX['built_at'] < _BANK_INDEX_TTL_SECONDS):
        return _BANK_INDEX['data']
    rows, tokens, by_industry = {}, {}, {}
    for row_id, topic, industry, text in (FAQQuestion.objects.exclude(topic__in=BANK_TOPICS)
                                          .values_list('id', 'topic', 'industry', 'question_text')):
        topic_l, industry_l, text_l = (topic or '').lower(), (industry or '').lower(), (text or '').lower()
        rows[row_id] = (topic_l, industry_l, text_l)
        for word in set(re.findall(r'[a-z0-9]+', topic_l + ' ' + text_l)):
            tokens.setdefault(word, set()).add(row_id)
        by_industry.setdefault(industry_l, set()).add(row_id)
    _BANK_INDEX['data'] = (rows, tokens, by_industry)
    _BANK_INDEX['built_at'] = now
    return _BANK_INDEX['data']


def _skill_question_ids(resume_text, skills, industries=None, is_it=None):
    """{resume skill: [FAQQuestion ids about it]} for the candidate's hard skills.

    The strongest signal of what to ask is the skill list itself: a question is
    about a skill when its topic or question names the skill as a whole word
    ("autocad designcenter", "What is Django middleware?"), or its industry IS the
    skill (the AutoCAD sheet). Matching topics against the whole resume text was
    missing these — a Mechanical resume listing SolidWorks/AutoCAD/welding got
    general automotive questions instead.
    """
    hard = sorted({
        s.strip().lower() for s in extract_resume_skills(resume_text, skills)
        if s and len(s.strip()) >= 2 and s.strip().lower() not in _SOFT_SKILLS
    })
    if not hard:
        return {}
    rows, tokens, by_industry = _domain_bank_index()
    in_domain, elsewhere = {}, {}
    wanted = {i.lower() for i in (industries or [])}
    # A non-IT candidate is never asked from the software industries, whatever
    # their resume happens to name. "SQL" on a commerce/analyst/HR resume was
    # matching the IT bank here and, because that skill had no questions in the
    # candidate's own industries, the cross-industry fallback below let it
    # through — SQL questions in a non-IT interview.
    banned = set() if is_it is not False else {i.lower() for i in IT_ONLY_INDUSTRIES}
    for s in hard:
        # Candidate rows share every word of the skill; the regex then keeps
        # whole-phrase hits only ("git" must not match "digital", "java" must
        # not match "javascript", "ci/cd" must appear as written).
        words = re.findall(r'[a-z0-9]+', s)
        candidates = set.intersection(*(tokens.get(w, set()) for w in words)) if words else set()
        pat = re.compile(r'(?<![a-z0-9])' + re.escape(s) + r'(?![a-z0-9])')
        matches = {i for i in candidates if pat.search(rows[i][0]) or pat.search(rows[i][2])}
        matches |= by_industry.get(s, set())
        for row_id in matches:
            industry_l = rows[row_id][1]
            if industry_l in banned:
                continue
            bucket = in_domain if (not wanted or industry_l in wanted or industry_l == s) else elsewhere
            bucket.setdefault(s, []).append(row_id)
    # A skill word means different things in different fields: "casting" is
    # concrete work to a Civil engineer and metal forming in manufacturing;
    # "documentation" is a drawing package in heavy industry and an Excel
    # tracker to a B.Com admin fresher. Once we know the candidate's
    # industries, a match OUTSIDE them is that collision, not a real signal —
    # a commerce resume listing "Documentation" was being handed
    # "engineering drawing and documentation" through this fallback.
    #
    # The fallback therefore applies ONLY when no industry could be detected
    # at all, where any on-skill question beats none. The slot count is never
    # at risk: the caller's own/general tiers are industry-scoped and fill
    # whatever the skills do not.
    if not wanted:
        for s, ids in elsewhere.items():
            in_domain.setdefault(s, ids)
    return in_domain


def _matching_bank_topics(resume_text, skills):
    """FAQQuestion topics the candidate's skills, projects or resume text mention.

    Matching on the whole resume (not just the skills list) is what pulls in
    topics named only in the projects/experience sections.
    """
    from career_app.models import FAQQuestion

    from django.core.cache import cache

    haystack = ' '.join([s for s in (skills or []) if s] + [resume_text or '']).lower()
    if not haystack.strip():
        return []
    # Word-boundary matching without a regex per topic (~1.4k topics, more than
    # Python's regex cache holds, so every call recompiled them all): with both
    # sides reduced to space-separated words, " java " is found in the padded
    # haystack but not inside "javascript".
    padded = ' ' + ' '.join(re.findall(r'\w+', haystack)) + ' '

    # The topic list only changes when a question bank is imported.
    topics = cache.get('faq_domain_topics')
    if topics is None:
        topics = list(
            FAQQuestion.objects.exclude(topic__in=BANK_TOPICS)
            .values_list('topic', flat=True).distinct()
        )
        cache.set('faq_domain_topics', topics, 600)

    def _mentions(term):
        term = term.strip()
        if len(term) < 2:
            return False
        if re.match(r'\w', term) and re.search(r'\w$', term):
            # Word-boundary match so "java" does not match "javascript".
            return ' ' + ' '.join(re.findall(r'\w+', term)) + ' ' in padded
        # Terms with punctuation (c++, aml/kyc) have no usable word boundary.
        return term in haystack

    matched = []
    for topic in topics:
        topic = (topic or '').strip()
        if len(topic) < 2:
            continue
        if _mentions(topic):
            matched.append(topic)
            continue
        # Compound topics ("docker & containers", "linux & shell", "git & version
        # control") are never written that way on a resume, so the whole-string
        # match above always missed them and the candidate got every domain
        # question from whichever single-word topic did match. Fall back to the
        # topic's component terms. Terms under 3 characters and generic filler
        # are skipped so "it, digital & technology staffing" cannot match the
        # word "it" in any resume.
        for part in re.split(r'\s*[&/,]\s*', topic):
            part = part.strip()
            if len(part) < 3 or part in TOPIC_STOPWORDS:
                continue
            if _mentions(part):
                matched.append(topic)
                break
    return matched


# Generic words that appear across most industries' topic names — excluded from
# the industry-detection vocabulary so a common word like "management" or
# "engineering" doesn't make every industry look relevant to every resume.
_GENERIC_INDUSTRY_WORDS = frozenset({
    'management', 'support', 'general', 'other', 'others', 'services', 'systems',
    'system', 'technology', 'technologies', 'staffing', 'control', 'design',
    'process', 'processes', 'development', 'engineering', 'technical', 'solutions',
    'solution', 'operations', 'operation', 'workforce', 'industrial', 'industries',
    'industry', 'planning', 'basics', 'fundamentals', 'concepts', 'tools',
    'analysis', 'quality', 'data', 'project', 'projects', 'programs', 'program',
    # Cross-domain words that appear in IT topic names but also in many non-IT
    # resumes (a Civil QA/QC resume has "testing", "monitoring", "quality
    # control"). Excluded so they don't make "it & software" look relevant to a
    # non-software candidate and pull in Python/lists/storage questions.
    'testing', 'monitoring', 'storage', 'backup', 'logging', 'observability',
    'performance', 'security', 'networking', 'database', 'databases', 'reliability',
    'standard', 'library', 'features', 'advanced', 'patterns', 'handling',
    'structures', 'configuration', 'best', 'practices', 'providers', 'cloud',
    # Office / business words that live in EVERY industry's topic names and in
    # every resume, so they carry no signal but dominate the score by sheer
    # count. "documentation" was the worst: a B.Com admin fresher listing it
    # as an MS-Office skill voted for 'engineering & heavy industries' and was
    # asked to explain engineering drawing and documentation. Likewise
    # 'business'/'communication'/'employee'/'experience' made 'global
    # capability centres' outrank the back-office industry that actually fit.
    'documentation', 'document', 'documents', 'reporting', 'reports', 'report',
    'business', 'communication', 'communications', 'employee', 'employees',
    'experience', 'knowledge', 'level', 'levels', 'full', 'team', 'teams',
    'with', 'work', 'working', 'tracking', 'skills', 'skill', 'training',
    'requirements', 'coordination', 'review', 'reviews', 'metrics',
    # Resume boilerplate. These are section headings and filler, not evidence
    # of a field, but they collide with real topic words: "Excel-BASED tracker"
    # voted for refinery & petrochemical, "Bachelor of COMMERCE" for
    # warehousing & industrial logistics, and the CERTIFICATIONS / personal
    # INFORMATION headings for cybersecurity and construction.
    'based', 'commerce', 'certifications', 'certification', 'information',
    'summary', 'objective', 'declaration', 'education', 'languages',
    'profile', 'career', 'personal', 'details', 'responsibilities',
})


# Purely software/IT industries. A candidate who is not a software/IT profile
# (see _is_it_profile) is never served questions from these, no matter how many
# generic English words ("lists", "testing", "control") their resume shares with
# a programming topic name.
IT_ONLY_INDUSTRIES = frozenset({
    'it & software',
    'data, cloud & cybersecurity',
    'ai & machine learning',
    'technical support & engineering',
})


# Core-engineering skills that reliably anchor a resume to an industry, even
# when the resume is thin and its bag-of-words barely overlaps the subtopic
# vocabulary (e.g. a Diploma Mechanical fresher). These are added to the
# detected industries directly.
_SKILL_INDUSTRY_HINTS = [
    # Distinctive mechanical skills ONLY — shared words like "welding",
    # "fabrication" or "machining" also appear on Civil QA/QC resumes, so they
    # must not anchor a resume to manufacturing/automotive.
    (('solidworks', 'catia', 'creo', 'nx', 'cnc', 'gd&t', 'thermodynamics',
      'fluid mechanics', 'pneumatics', 'hydraulics', 'sheet metal', 'tooling',
      'ansys', 'powertrain', 'lean manufacturing'),
     ['manufacturing & advanced mfg.', 'automotive & electric vehicles',
      'engineering & heavy industries']),
    (('revit', 'staad', 'etabs', 'concrete technology', 'geotechnical',
      'structural analysis', 'surveying', 'construction management',
      'site supervision', 'site engineering'),
     ['infrastructure & construction', 'epc & pmc']),
]


def _skill_hinted_industries(haystack):
    hinted = []
    for skills, industries in _SKILL_INDUSTRY_HINTS:
        if any(re.search(r'\b' + re.escape(s) + r'\b', haystack) for s in skills):
            for ind in industries:
                if ind not in hinted:
                    hinted.append(ind)
    return hinted


def detect_resume_industries(resume_text, skills=None):
    """Industries (FAQQuestion.industry) whose vocabulary the resume overlaps most.

    Domain questions are gated to these industries so a Civil-Engineering /
    QA-QC resume is never handed a Python, storage-and-backup or software-testing
    question just because a generic word overlaps. Scoring is a bag-of-words
    overlap between the resume and each industry's subtopic words (minus generic
    filler), which is far more robust on this taxonomy than matching whole
    subtopic phrases. Returns the industries within 60% of the top score
    (min 3, max 8); empty when nothing overlaps, so the caller falls back to the
    unscoped bank rather than blocking the interview.
    """
    from career_app.models import FAQQuestion

    haystack = ' '.join([s for s in (skills or []) if s] + [resume_text or '']).lower()
    resume_words = set(re.findall(r'[a-z]{4,}', haystack))
    if not resume_words:
        return []

    rows = (
        FAQQuestion.objects.exclude(topic__in=BANK_TOPICS).exclude(industry='')
        .values_list('industry', 'topic').distinct()
    )
    vocab = {}
    word_df = {}   # how many industries each word appears in (document frequency)
    for industry, topic in rows:
        for w in re.findall(r'[a-z]{4,}', topic or ''):
            if w in _GENERIC_INDUSTRY_WORDS:
                continue
            v = vocab.setdefault(industry, set())
            if w not in v:
                v.add(w)
                word_df[w] = word_df.get(w, 0) + 1

    # Score each industry by the DISTINCTIVE resume words it owns: a word shared
    # across many industries (df high) is near-worthless as a signal — "testing"
    # or "control" in a Civil resume must not vote for "it & software". Weight
    # each matched word by 1/df and ignore words spread across >6 industries.
    scored = {}
    for ind, words in vocab.items():
        s = sum(1.0 / word_df[w] for w in (words & resume_words) if word_df[w] <= 6)
        if s > 0:
            scored[ind] = s
    if not scored:
        return []

    # A non-IT profile never draws from the pure-software industries.
    if not _is_it_profile(resume_text, skills):
        scored = {ind: s for ind, s in scored.items() if ind not in IT_ONLY_INDUSTRIES}
        if not scored:
            return []

    top = max(scored.values())
    cutoff = top * 0.6
    keep = sorted(scored, key=lambda i: -scored[i])
    kept = [ind for ind in keep if scored[ind] >= cutoff]
    # Keep only industries that clear the cutoff. Do NOT pad up to three: forcing
    # a minimum of three admitted noise industries whenever the resume matched
    # fewer (an HR/admin/B.Com fresher pulling 'electrical & industrial
    # automation' and 'epc & pmc', which then served CAD-drawing and PLC domain
    # questions). Guarantee only the single strongest so a thin resume still gets
    # on-domain questions instead of an empty gate.
    if not kept:
        kept = keep[:1]

    # Skill-anchored industries take priority — they come from unambiguous
    # core-engineering skills, so they lead even when the noisy bag-of-words
    # scored an unrelated industry higher.
    hinted = _skill_hinted_industries(haystack)
    if hinted:
        # High-confidence skill anchors lead, and the noisy bag-of-words tail is
        # trimmed hard so a thin engineering resume doesn't leak telecom/defence.
        kept = (hinted + [ind for ind in kept if ind not in hinted])[:len(hinted) + 1]
        return kept
    return kept[:8]


def _domain_question_pool(is_it, relevant_industries):
    """The domain questions a candidate may be asked, IT gate included.

    detect_resume_industries() already drops the IT-only industries for a
    non-IT profile, but it returns [] when that leaves nothing scored — and an
    empty list meant "do not filter", which reopened the WHOLE bank and served
    SQL/Python questions to non-IT candidates. The IT exclusion is therefore
    applied here, on the pool itself, where no empty result can bypass it.
    """
    from career_app.models import FAQQuestion

    pool = FAQQuestion.objects.exclude(topic__in=BANK_TOPICS)
    if relevant_industries:
        pool = pool.filter(industry__in=relevant_industries)
    if not is_it:
        pool = pool.exclude(industry__in=IT_ONLY_INDUSTRIES)
    return pool


def _sample_questions(queryset, count, seen, stale, allow_repeats=True):
    """Pick `count` random rows, preferring questions the candidate has never seen.

    `seen`  - texts already used in THIS interview (never reused).
    `stale` - texts used in the candidate's PAST interviews (reused only if the
              matching pool is too small to fill the slot, and never when
              `allow_repeats` is False).

    Duplicate checks are semantic (see _is_semantic_duplicate), not exact-text
    only, and are applied incrementally as rows are picked - a random sample
    of ~80 rows can easily contain two differently-worded rows on the same
    question family, and both being picked in the same call would defeat the
    whole point of the check.
    """
    if count <= 0:
        return []

    # Randomise by shuffling PRIMARY KEYS, not with ORDER BY RAND(). On the
    # ~40k-row domain bank, order_by('?') is a full-table scan + filesort that
    # made each live domain-question pick visibly slow; pulling just the ids
    # (an index-only read), shuffling them in Python and fetching a small
    # random slice is orders of magnitude faster and gives the same randomness.
    import random
    ids = list(queryset.values_list('id', flat=True))
    if not ids:
        return []
    random.shuffle(ids)
    sample_ids = ids[:max(count * 10, 80)]
    rows = list(queryset.filter(id__in=sample_ids))
    random.shuffle(rows)

    picked = []
    picked_texts = []  # grows as we pick, so within-batch near-duplicates are caught too
    repeats_pool = []

    for row in rows:
        if len(picked) >= count:
            break
        if _is_semantic_duplicate(row.question_text, seen) or _is_semantic_duplicate(row.question_text, picked_texts):
            continue
        if _is_semantic_duplicate(row.question_text, stale):
            repeats_pool.append(row)
            continue
        picked.append(row)
        picked_texts.append(row.question_text)

    if allow_repeats and len(picked) < count:
        for row in repeats_pool:
            if len(picked) >= count:
                break
            if _is_semantic_duplicate(row.question_text, picked_texts):
                continue
            picked.append(row)
            picked_texts.append(row.question_text)

    for text in picked_texts:
        seen.add(text)
    return picked


# Difficulty mix for each 5-question HR block (Q1-5 behavioural, Q6-10
# experience/academic), by years of experience. Every level gets at least one
# Hard question so the HR round probes the candidate instead of staying easy.
def _hr_difficulty_mix(years, count=5):
    if years <= 2:
        mix = ['Easy', 'Easy', 'Intermediate', 'Intermediate', 'Hard']
    elif years <= 5:
        mix = ['Easy', 'Intermediate', 'Intermediate', 'Hard', 'Hard']
    else:
        mix = ['Intermediate', 'Intermediate', 'Hard', 'Hard', 'Hard']
    return mix[:count]


# Experience-bank questions a fresher can honestly answer (studies, coursework,
# internships). Freshers draw from these plus the academic/project bank.
_FRESHER_SAFE_RE = re.compile(
    r'\b(school|college|universit\w*|academic\w*|course\w*|class\w*|stud(?:y|ies|ent\w*)|'
    r'graduat\w*|degree|education\w*|professor\w*|campus|thesis)\b',
    re.IGNORECASE,
)

# Questions that presume a senior/managerial past (leading people, running
# programs, M&A). Never asked to a fresher.
_SENIOR_ONLY_RE = re.compile(
    r"\b(direct reports?|individual contributor|merger|acquisition|succession|"
    r"hir(?:e|ed|ing)|layoffs?|headcount|executives?|board|p&l|budget|"
    r"(?:intern|internship|onboarding|training) program\w*|for an intern|intern's|"
    # Hiring decisions: a fresher has never screened, shortlisted or chosen
    # between candidates. "How do you evaluate cultural fit versus skill fit?"
    # was reaching an HR fresher's Academic/Project block through the 'hr' theme.
    r"cultural fit|skill fit|candidates?|shortlist\w*|screening|offer letter|"
    r"interview panel|talent pipeline|recruit(?:ing|ment) strategy|"
    r"your (?:reports|organi[sz]ation)|(?:lead|led|leading|manag\w+) (?:a|your|the) team|"
    r"as a (?:manager|leader|director))\b",
    re.IGNORECASE,
)

# Questions that assume the candidate already held a job. A fresher gets a
# domain-matched experience question only if it doesn't assume one.
_ASSUMES_JOB_RE = re.compile(
    r"\b(?:(?:previous|past|current|last|prior) (?:jobs?|roles?|employers?|compan(?:y|ies)|positions?)|"
    r"at work|in past roles|at a previous job|in your current role|your time in)\b",
    re.IGNORECASE,
)

# Questions that presume the candidate has held a job, even though they never
# say "previous role". A fresher has no boss, no stakeholders, no colleagues
# and no performance review, so "Tell me about a time you disagreed with your
# boss's approach" is unanswerable for them — they were reaching the
# Behavioural block, which only filtered for SENIORITY, not for employment.
# Deliberately narrow: "team", "project" and "deadline" are NOT here, because
# a college team, a college project and a submission deadline are all real
# fresher experience.
_ASSUMES_WORKPLACE_RE = re.compile(
    r"\b(your boss|my boss|the boss|your manager|senior leadership|senior management|"
    r"stakeholders?|formal authority|colleagues?|co-?workers?|cross-functional|"
    r"performance review|promotions?|your organi[sz]ation|the organi[sz]ation|"
    r"workplace|office politics|your company|the company|your employer|"
    r"a client|the client|clients|customers?|your role at|in your role|"
    r"direct reports?|your team at|at your job|on the job|at the office|"
    r"contract negotiation|deal or partnership|business unit|your department)\b",
    re.IGNORECASE,
)


# The HR workbook's experience questions come in themed groups (ERP, CRM, Agile,
# healthcare, supply chain...). theme -> (question pattern, resume pattern): a
# themed question is asked only when the resume shows that theme, so a Civil
# engineer is never asked about CRM rollouts. A question matching no theme is
# generic ("What professional achievement are you most proud of?").
_HR_THEMES = {
    'sales': (r"\bsales\b|business development|quota|close (?:difficult )?deals|deal or partnership|new business",
              r"\bsales\b|business development|quota|revenue target|account executive"),
    'product': (r"product (?:development|launch|requirements)|bring to market|shape a product",
                r"product (?:manager|management|development|owner|launch)"),
    'regulatory': (r"regulat\w*|complian\w*|auditors?|\bhipaa\b|\bsec\b|finra",
                   r"regulat\w*|complian\w*|\baudit\w*|\bhipaa\b|\bsebi\b|\brbi\b"),
    'vendors': (r"vendors?|suppliers?", r"vendor|supplier|procurement|purchas\w*|sourcing"),
    'research': (r"research|peer review|paper\b|publishing|publication",
                 r"research|thesis|publication|journal|paper\b"),
    'quality': (r"quality (?:assurance|standards|issue|checks)",
                r"quality (?:assurance|control|engineer\w*|management)|\bqa\b|\bqc\b|inspection|iso ?9001|six sigma"),
    'customer_success': (r"customer success|support role|customer satisfaction|churn|onboarding new customers",
                         r"customer (?:success|support|service|care)|\bcsat\b|\bnps\b|churn|help ?desk"),
    'marketing': (r"marketing|campaign|brand positioning|seo\b|content (?:strategy|plan)|keyword research|"
                  r"piece of content|social media",
                  r"marketing|campaign|\bbrand\w*|\bseo\b|content writ\w*|social media|copywrit\w*"),
    'software': (r"programming languages|software project|code review|\bbug\b|architected|mobile|"
                 r"devops|ci/cd|continuous integration|deployment|api or developer|cloud|on-premises",
                 r"python|java\b|javascript|typescript|c\+\+|c#|golang|react|django|node|flutter|kotlin|"
                 r"swift|(?:software|web|app|backend|front[- ]?end|full[- ]?stack) developer|programming|\baws\b|azure|"
                 r"\bgcp\b|devops|docker|kubernetes"),
    'agile': (r"\bagile\b|scrum|sprint|waterfall", r"\bagile\b|scrum|sprint|waterfall|jira|kanban|\bpmp\b"),
    'crm': (r"\bcrm\b", r"\bcrm\b|salesforce|hubspot|zoho"),
    'erp': (r"\berp\b", r"\berp\b|\bsap\b|oracle (?:erp|ebs|fusion|financials)|netsuite|tally|dynamics 365"),
    'experiments': (r"a/b tests?|experiment\w*|statistical significance",
                    r"a/b test\w*|experiment\w*|statistic\w*|hypothesis"),
    'ux': (r"\bux\b|\bui\b|user interface|user experience|usability|design aesthetics|user research|"
           r"user interviews|customer research|qualitative research",
           r"\bux\b|\bui\b|figma|user experience|user interface|usability|adobe xd|user research"),
    'public_sector': (r"public sector|government",
                      r"public sector|government (?:department|agency|project|body|organi[sz]ation)|\bpsu\b|"
                      r"ministry|municipal corporation"),
    'nonprofit': (r"nonprofit|non-profit|grants?\b|funder", r"non-?profit|\bngo\b|charity|grant\b|fundrais\w*"),
    'corporate_finance': (r"merger|acquisition|m&a|post-merger|fundrais\w*|\bipo\b|investors?|due diligence|"
                          r"funding round|financial services",
                          r"merger|\bm&a\b|\bipo\b|investor relations|venture capital|funding round|"
                          r"due diligence|investment banking|financial services"),
    'automation': (r"automat\w*|\brpa\b", r"automat\w*|\brpa\b|uipath|scripting|macros?\b"),
    'ai_ml': (r"\bai\b|machine learning|ai/ml", r"\bai\b|machine learning|\bml\b|deep learning|tensorflow|"
                                               r"pytorch|scikit|\bnlp\b|\bllms?\b"),
    'supply_chain': (r"supply chain|logistics", r"supply chain|logistic\w*|warehous\w*|inventory|\bscm\b"),
    'manufacturing': (r"manufacturing|production floor|operations (?:role|environment)|equipment|throughput",
                      r"manufactur\w*|shop floor|production (?:line|planning|engineer\w*|floor|supervisor)|"
                      r"plant (?:operations|engineer\w*)|assembly line|\bcnc\b|machining"),
    'healthcare': (r"healthcare|patient", r"health ?care|hospital|patient|clinical|medical|pharma\w*"),
    'legal': (r"contracts?\b|legal|clause",
              r"legal|contract (?:management|negotiation|drafting|review)|\blaw\b|lawyer|advocate"),
    'events': (r"\bevents?\b|conferences?|offsites?",
               r"event (?:management|planning|coordinat\w*)|organi[sz]ed (?:an? |the )?(?:event|conference|fest)|"
               r"conference|exhibition"),
    'communications': (r"crisis communications|crisis messaging|draft a message|public relations|"
                       r"media outreach|journalists|\bpress\b|\bpr\b",
                       r"corporate communications|public relations|\bpr\b|media relations|press releases?"),
    'localization': (r"locali[sz]\w*|translation|different markets",
                     r"locali[sz]\w*|translat\w*|multilingual"),
    'documentation': (r"technical (?:or process )?documentation|documentation (?:standards|system|up to date)",
                      r"documentation|technical writ\w*"),
    'security': (r"security", r"security|cyber|\bsoc\b|siem|penetration|firewall|iso 27001"),
    'ecommerce': (r"e-commerce|conversion rate|checkout|inventory or order",
                  r"e-?commerce|shopify|magento|woocommerce|order management"),
    'expansion': (r"new markets?|new country|international expansion|market is ready",
                  r"expansion|market entry|export|international business"),
    'hr': (r"hiring|interviewing a candidate|candidate pool|cultural fit|diversity|succession|"
           r"performance (?:review|management|goals)|calibrate ratings",
           r"recruit\w*|hiring|talent acquisition|\bhr\b|human resources|people management"),
    'freelance': (r"freelanc\w*|contractor|independent worker", r"freelanc\w*|self-employed|independent consultant"),
    'volunteer': (r"volunteer|extracurricular|outside of paid work",
                  r"volunteer\w*|\bnss\b|\bncc\b|extracurricular|community service"),
    'remote': (r"remote|hybrid|time zones|distributed|different locations",
               r"remote|hybrid|work from home|distributed team"),
    'international': (r"international (?:teams|clients)|across countries|cultural differences|"
                      r"global(?:ly)? (?:organization|distributed|team)|languages do you speak",
                      r"international (?:clients|projects|teams)|overseas|multinational|\bmnc\b"),
    'startup': (r"startup", r"startup|start-up|founder"),
    'budget': (r"budget|financial reporting|forecasting|cost[- ](?:saving|reduction|cutting|savings)",
               r"budget\w*|\bp&l\b|cost (?:saving|reduction|control|estimation)|forecast\w*"),
}
_HR_THEMES = {
    name: (re.compile(q, re.IGNORECASE), re.compile(r, re.IGNORECASE))
    for name, (q, r) in _HR_THEMES.items()
}


@functools.lru_cache(maxsize=5000)
def _is_senior_question(text):
    return bool(_SENIOR_ONLY_RE.search(text))


@functools.lru_cache(maxsize=256)
def _resume_themes(haystack):
    return frozenset(name for name, (_q, r) in _HR_THEMES.items() if r.search(haystack))


@functools.lru_cache(maxsize=5000)
def _question_themes(text):
    # Cached: the HR bank's ~800 question texts are fixed, and every interview
    # used to re-run ~40 theme regexes over all of them.
    return frozenset(name for name, (q, _r) in _HR_THEMES.items() if q.search(text))


def _split_hr_rows_by_resume(rows, resume_text, skills=None):
    """Split HR-bank rows into (resume_anchored, generic) and drop mismatches.

    A question on a theme (ERP, Agile, healthcare... see _HR_THEMES) is asked
    only when the resume shows every theme it touches, and is then preferred
    over generic ones. A question with no theme suits any resume.
    """
    haystack = f"{resume_text or ''}\n{' '.join(skills or [])}"
    resume_themes = _resume_themes(haystack)

    anchored, generic = [], []
    for row in rows:
        themes = _question_themes(row.question_text)
        if not themes:
            generic.append(row)
        elif themes <= resume_themes:
            anchored.append(row)
        # else: about a field this resume doesn't show — never asked.
    return anchored, generic


def _sample_hr_block(rows, resume_text, skills, years, seen, stale, count=5,
                     mix=None, anchored_budget=3):
    """Pick `count` random HR-bank rows for one Q1-5 / Q6-10 block.

    Random within an experience-based difficulty mix, resume-anchored questions
    first, then generic ones, then any tier if a tier runs dry. Returns the rows
    ordered Easy -> Hard.
    """
    from collections import Counter
    from career_app.models import FAQQuestion

    import random

    anchored, generic = _split_hr_rows_by_resume(rows, resume_text, skills)
    # Themed questions already asked in a past interview are dropped before the
    # one-per-theme pick below, so a theme is represented by a fresh question.
    anchored = [r for r in anchored if not _is_semantic_duplicate(r.question_text, stale)]
    # One question per theme per block — themed questions come in groups of
    # five, so without this a block could be three volunteering questions.
    random.shuffle(anchored)
    used_themes, diverse = set(), []
    for row in anchored:
        themes = _question_themes(row.question_text)
        if not themes & used_themes:
            used_themes |= themes
            diverse.append(row)
    anchored = diverse

    tier_of = {}
    for tier, keys in DIFFICULTY_DB_KEYS.items():
        for key in keys:
            tier_of[key] = tier

    def _pick(pool, n, tier=None, allow_repeats=False):
        ids = [r.id for r in pool if tier is None or tier_of.get(r.difficulty) == tier]
        return _sample_questions(FAQQuestion.objects.filter(id__in=ids), n, seen, stale,
                                 allow_repeats=allow_repeats)

    # `anchored_budget` of the 5 (default 3) are tied to the resume's own
    # themes; the rest stay generic so the block still covers standard HR ground.
    picked = []
    for tier, n in Counter(mix or _hr_difficulty_mix(years, count)).items():
        got = _pick(anchored, min(n, anchored_budget), tier)
        anchored_budget -= len(got)
        got += _pick(generic, n - len(got), tier)
        picked += got
    # A dry tier borrows fresh questions from any tier; a question from a past
    # interview is repeated only once the whole bank has been used up.
    for allow_repeats in (False, True):
        for pool in (generic, anchored):
            picked_ids = {r.id for r in picked}
            picked += _pick([r for r in pool if r.id not in picked_ids], count - len(picked),
                            allow_repeats=allow_repeats)

    order = {'Easy': 0, 'Intermediate': 1, 'Hard': 2}
    picked.sort(key=lambda r: order.get(tier_of.get(r.difficulty), 0))
    return [(row, tier_of.get(row.difficulty, 'Easy')) for row in picked[:count]]


def generate_interview_questions(resume_text, job_description, skills=None, user=None, domain_count=10):
    """Build a mock interview from the FAQQuestion bank in the database.

    No LLM/API call is made here — that was costing tokens on every interview.
    Questions are sampled from the DB and calibrated to the candidate's skills,
    projects, IT/Non-IT domain and years of experience (see
    classify_candidate_type for the resulting IT_EXPERIENCED / IT_FRESHER /
    NON_IT_EXPERIENCED / NON_IT_FRESHER label):

        Q1-5   Behavioural / HR
        Q6-10  Experience-based (candidates with >1 year of professional
               experience) or Academic/Project-based (Fresher/Entry-Level,
               <=1 year — see ACADEMIC_PROJECT_QUESTIONS)
        Q11-20 Domain questions matching the candidate's topics — technical/
               skill-based for an IT profile, role/process-based for a
               Non-IT profile (see PROCESS_TOPICS) — with the difficulty mix
               set by their years of experience.

    `domain_count` controls how many of the Q11-20 domain questions are
    generated here, up front. Pass 0 to build only Q1-10 and let the caller
    select domain questions one at a time as the interview progresses (see
    select_next_domain_question) - that's what makes difficulty genuinely
    adaptive to the candidate's actual answers, rather than fixed by years
    of experience alone before the interview even starts. Default is 10
    (the original, non-adaptive, all-at-once behavior) so any other caller
    is unaffected.

    Sampling is randomised and skips questions the candidate was asked in earlier
    sessions, so repeat interviews produce a different paper. Duplicate
    avoidance is semantic (see _is_semantic_duplicate), not exact-text only.

    Answer evaluation still calls the LLM — see `evaluate_answer`.
    """
    from django.db.models import Q
    from career_app.models import FAQQuestion
    import random
    import logging

    logger = logging.getLogger(__name__)

    skills = skills or []
    is_it = _is_it_profile(resume_text, skills)

    # Difficulty mix for the domain questions, calibrated to experience.
    years = extract_experience_years(resume_text)
    is_experienced = classify_experience_level(years) not in ('fresher', 'entry_level')
    candidate_type = 'IT_EXPERIENCED' if (is_it and is_experienced) else \
        'IT_FRESHER' if is_it else \
        'NON_IT_EXPERIENCED' if is_experienced else 'NON_IT_FRESHER'
    if domain_count <= 0:
        tech_diffs = []
    elif years <= 2:
        tech_diffs = (['Easy'] * 6 + ['Intermediate'] * 3 + ['Hard'] * 1)[:domain_count]
    elif years <= 5:
        tech_diffs = (['Easy'] * 2 + ['Intermediate'] * 5 + ['Hard'] * 3)[:domain_count]
    else:
        tech_diffs = (['Intermediate'] * 4 + ['Hard'] * 6)[:domain_count]

    final_questions = []
    seen = set()
    stale = _previously_asked_texts(user)

    def _add(topic, difficulty, text, question_type='theory'):
        if text and not _is_semantic_duplicate(text, [q['question'] for q in final_questions]):
            final_questions.append({
                'topic': topic,
                'difficulty': difficulty,
                'question': text,
                'question_type': question_type,
                'candidate_type': candidate_type,
            })
            return True
        return False

    # ── Q1-5: Behavioural / HR ────────────────────────────────────────────────
    # Random from the full behavioural bank, Easy->Hard mix by experience, with
    # questions tied to the resume's field preferred (see _sample_hr_block).
    hr_fields = ('id', 'question_text', 'difficulty')
    behavioural_rows = list(FAQQuestion.objects.filter(topic=BEHAVIOURAL_TOPIC).only(*hr_fields))
    # Questions that presume leading people, hiring or M&A only go to candidates
    # with enough years to have done it — not to freshers or juniors (<=2 years).
    senior_ok = years > 2
    if not senior_ok:
        # Seniority is not the only thing a fresher lacks: they also have no
        # boss, no stakeholders, no colleagues and no performance review, so
        # the workplace-assuming questions go too. Behavioural used to filter
        # for seniority ONLY, which is how "Tell me about a time you disagreed
        # with your boss's approach" reached a B.Com fresher with no job.
        behavioural_rows = [
            r for r in behavioural_rows
            if not _is_senior_question(r.question_text)
            and not _ASSUMES_WORKPLACE_RE.search(r.question_text)
            and not _ASSUMES_JOB_RE.search(r.question_text)
        ]
    # A fresher's Hard question comes from the fresher bank (Q6-10): the
    # behavioural bank's Hard questions assume years of work and people to manage.
    behavioural_mix = None if is_experienced else ['Easy', 'Easy', 'Intermediate', 'Intermediate', 'Intermediate']
    for row, tier in _sample_hr_block(behavioural_rows, resume_text, skills, years, seen, stale,
                                      mix=behavioural_mix):
        _add('Behavioural', tier, row.question_text)
    _top_up_from_bank(final_questions, BEHAVIOURAL_QUESTIONS, 'Behavioural', 5, seen,
                      fresher=not senior_ok)

    # ── Q6-10: Experience-based (Experienced) or Academic/Project-based (Fresher) ──
    # A candidate with <=1 year of professional experience has no past job an
    # "experience" question can honestly be about, so this section swaps to
    # the academic/project bank (plus the experience questions that are about
    # studies/internships) for Fresher/Entry-Level candidates instead.
    experience_rows = list(FAQQuestion.objects.filter(topic=EXPERIENCE_TOPIC).only(*hr_fields))
    if is_experienced:
        pool = experience_rows if senior_ok else [
            r for r in experience_rows if not _is_senior_question(r.question_text)]
        for row, tier in _sample_hr_block(pool, resume_text, skills, years, seen, stale):
            _add('Experience', tier, row.question_text)
        _top_up_from_bank(final_questions, EXPERIENCE_QUESTIONS, 'Experience', 10, seen)
    else:
        # Studies/coursework questions, plus experience questions on the resume's
        # own themes (e.g. "Describe a software project you contributed to" for
        # an IT fresher) as long as they don't assume a past job or seniority.
        themed_rows, _generic = _split_hr_rows_by_resume(experience_rows, resume_text, skills)
        fresher_rows = list(FAQQuestion.objects.filter(topic=ACADEMIC_TOPIC).only(*hr_fields))
        fresher_rows += [
            row for row in experience_rows
            if (_FRESHER_SAFE_RE.search(row.question_text) or row in themed_rows)
            and not _is_senior_question(row.question_text)
            and not _ASSUMES_JOB_RE.search(row.question_text)
            and not _ASSUMES_WORKPLACE_RE.search(row.question_text)
        ]
        # One themed question at most: most themed experience questions are
        # about a workplace, while the fresher bank already asks about the
        # candidate's own projects.
        for row, tier in _sample_hr_block(fresher_rows, resume_text, skills, years, seen, stale,
                                          anchored_budget=1):
            _add('Academic/Project', tier, row.question_text)
        _top_up_from_bank(final_questions, ACADEMIC_PROJECT_QUESTIONS, 'Academic/Project', 10, seen,
                          fresher=True)

    # ── Q11-20: Domain questions from the candidate's own topics ──────────────
    matched_topics = _matching_bank_topics(resume_text, skills)
    # Gate the domain pool to the candidate's actual industries FIRST. Without
    # this, a Civil-Engineering resume matched IT subtopics like "storage &
    # backup", "monitoring & logging" or "lists" (Python) purely on a shared
    # generic word, and got served Python/IT questions. Restricting the pool to
    # the resume's industries makes even the widen-to-"general" fallback stay
    # on-domain instead of pulling a random unrelated topic to reach 20.
    relevant_industries = detect_resume_industries(resume_text, skills)
    logger.info(
        "Interview bank: matched %d topic(s) (IT=%s) in industries %s: %s",
        len(matched_topics), is_it, relevant_industries or 'ALL',
        ', '.join(matched_topics[:10]) or 'none'
    )

    domain_qs = _domain_question_pool(is_it, relevant_industries)
    own_qs = domain_qs.filter(topic__in=matched_topics) if matched_topics else domain_qs.none()
    # The pool is already industry-scoped, so "general" (the widen fallback) is
    # every question in the candidate's own industries — still on-domain.
    general_qs = domain_qs

    # Imported staffing questions carry no difficulty label; treat them as
    # usable at any level rather than dropping them from every bucket.
    unlabelled = Q(difficulty__isnull=True) | Q(difficulty='')

    from collections import Counter
    import math
    diff_counts = Counter(tech_diffs)

    # Spread the domain questions across topics instead of letting one topic
    # (e.g. AWS, or the single "CNC machining" a Mechanical resume matched) fill
    # all 10 slots. Cap per topic at ceil(domain_count / N) where N is at least 3,
    # so even when only ONE skill-topic matched, that topic is capped (~4) and the
    # remaining slots are drawn from OTHER topics in the same industries (the
    # general/widen tier). Relaxed in a final pass if it would leave the paper short.
    distinct_topics = (
        list(own_qs.values_list('topic', flat=True).distinct()) if matched_topics else []
    )
    per_topic_cap = max(2, math.ceil(domain_count / max(3, len(distinct_topics))))
    domain_counts = Counter()

    def _add_domain(row, diff_label, respect_cap=True):
        t = row.topic
        if respect_cap and domain_counts[t] >= per_topic_cap:
            return False
        if _add(t.capitalize(), diff_label, row.question_text):
            domain_counts[t] += 1
            return True
        return False

    # Resume skills first: each slot goes to the skill asked about least so far,
    # so the questions spread across everything the candidate listed.
    skill_ids = _skill_question_ids(resume_text, skills, relevant_industries, is_it=is_it)
    skill_cap = max(2, math.ceil(domain_count / max(1, len(skill_ids)))) if skill_ids else 0
    skill_counts = Counter()

    def _fill_from_skills(needed, keys):
        for any_level in (False, True):   # a skill question at another level beats an off-skill one
            progress = True
            while needed > 0 and progress:
                progress = False
                order = sorted(skill_ids, key=lambda s: (skill_counts[s], random.random()))
                for s in order:
                    if needed <= 0:
                        break
                    if skill_counts[s] >= skill_cap:
                        continue
                    pool = FAQQuestion.objects.filter(id__in=skill_ids[s])
                    if not any_level:
                        pool = pool.filter(Q(difficulty__in=keys) | unlabelled)
                    for row in _sample_questions(pool, 1, seen, stale):
                        if _add(row.topic.capitalize(), diff_label, row.question_text):
                            skill_counts[s] += 1
                            domain_counts[row.topic] += 1
                            needed -= 1
                            progress = True
        return needed

    for diff_label in ['Easy', 'Intermediate', 'Hard']:
        needed = diff_counts.get(diff_label, 0)
        if needed <= 0:
            continue
        keys = DIFFICULTY_DB_KEYS[diff_label]
        needed = _fill_from_skills(needed, keys)

        # Then topics the resume text mentions, then the resume's industries,
        # widening only when a tier runs dry.
        tiers = [
            own_qs.filter(Q(difficulty__in=keys) | unlabelled),
            own_qs,
            general_qs.filter(Q(difficulty__in=keys) | unlabelled),
            general_qs,
        ]
        # Two passes: first honour the per-topic cap (spread), then, only if
        # still short, ignore it so the slot count is still met.
        for respect_cap in (True, False):
            if needed <= 0:
                break
            for tier in tiers:
                if needed <= 0:
                    break
                # Oversample so capped-out rows can be skipped without a re-query.
                for row in _sample_questions(tier, max(needed * 4, 20), seen, stale):
                    if needed <= 0:
                        break
                    if _add_domain(row, diff_label, respect_cap=respect_cap):
                        needed -= 1

        # Last resort when the bank has nothing suitable left for this slot —
        # e.g. an environment where the FAQQuestion domain bank hasn't been
        # imported yet. Without this, an IT candidate's technical questions
        # (Q11-20) could silently drop to 0 while Behavioural/Experience
        # still filled via their own in-code fallbacks, producing a
        # 10-question interview instead of 20.
        if needed > 0:
            fallback = (NON_IT_TECHNICAL_FALLBACK if not is_it else IT_TECHNICAL_FALLBACK)[:]
            random.shuffle(fallback)
            for text in fallback:
                if needed <= 0:
                    break
                if not _is_semantic_duplicate(text, seen):
                    seen.add(text)
                    _add('Domain', diff_label, text)
                    needed -= 1

    logger.info("Assembled %d interview question(s) from the database (0 API calls).",
                len(final_questions))
    return final_questions[:20]


# ── Adaptive difficulty for the domain portion (Q11-20) ─────────────────────
#
# generate_interview_questions() decides the WHOLE interview's domain
# difficulty mix once, up front, purely from years of experience. That is
# what the candidate's plan/level starts at, but a real adaptive interview
# has to keep adjusting as the candidate actually answers - someone who is
# breezing through Easy questions should get harder ones; someone who is
# struggling with Intermediate should not just keep receiving Intermediate.
#
# These two functions implement that: the view calls next_domain_difficulty()
# to decide what level the NEXT domain question should be at (based on the
# most recent domain answer's score), then select_next_domain_question() to
# actually pick one at that level - one question at a time, not the whole
# batch in advance.

_DIFFICULTY_ORDER = ['Easy', 'Intermediate', 'Hard']


def next_domain_difficulty(session):
    """Difficulty for the NEXT domain question in `session`, adapted to how
    the candidate scored (0-5) on the most recent domain question so far.

    First domain question: starts from the session's classified experience
    level (see classify_experience_level / _EXPERIENCE_DIFFICULTY_BOUNDS).
    After that: a 5/5 nudges difficulty up one level, 4/5 or 3/5 holds
    steady, 2 or below nudges it down one level - but never outside that
    experience level's floor/ceiling. A true Fresher can never be pushed to
    Hard by a lucky streak, and a Senior/Expert can never be dropped to Easy
    by one weak answer - both were possible before this bound existed.
    """
    experience_level = session.experience_level or classify_experience_level(
        extract_experience_years(session.resume.extracted_text or '')
    )
    start_difficulty, floor, ceiling = _EXPERIENCE_DIFFICULTY_BOUNDS.get(
        experience_level, _EXPERIENCE_DIFFICULTY_BOUNDS['mid_level']
    )
    floor_index = _DIFFICULTY_ORDER.index(floor)
    ceiling_index = _DIFFICULTY_ORDER.index(ceiling)

    domain_questions = list(session.questions.filter(order__gte=10).order_by('order'))
    if not domain_questions:
        return start_difficulty

    last_question = domain_questions[-1]
    try:
        last_score = last_question.answer.score
    except Exception:
        last_score = None

    current_index = (
        _DIFFICULTY_ORDER.index(last_question.difficulty)
        if last_question.difficulty in _DIFFICULTY_ORDER else floor_index
    )

    if last_score is None:
        next_index = current_index          # not answered yet - hold, don't guess
    elif last_score >= 5:
        next_index = current_index + 1
    elif last_score >= 3:
        next_index = current_index          # 3-4: maintain
    else:
        next_index = current_index - 1      # 0-2: ease off

    next_index = max(floor_index, min(ceiling_index, next_index))
    return _DIFFICULTY_ORDER[next_index]


def select_next_domain_question(session, difficulty):
    """Pick ONE domain/technical question at `difficulty` for `session`.

    Reuses the exact same topic-matching and tiered-fallback logic
    generate_interview_questions() uses for Q11-20, just for a single
    question instead of the whole batch, so a lazily-built adaptive
    interview and the old all-at-once one select from the same pool with
    the same preferences. Duplicate avoidance (exact + semantic) is applied
    against every question already asked in this session AND the
    candidate's past sessions, exactly like the batch path.

    Returns a dict shaped like one entry from generate_interview_questions()
    output (`topic`, `difficulty`, `question`, `question_type`), or None if
    truly nothing eligible remains anywhere (caller's safety fallback).
    """
    from django.db.models import Q
    from career_app.models import FAQQuestion
    import random

    resume_text = session.resume.extracted_text or ''
    skills = session.matching_skills or []
    is_it = _is_it_profile(resume_text, skills)
    years = extract_experience_years(resume_text)
    candidate_type = classify_candidate_type(resume_text, skills, years=years)

    seen = set(session.questions.values_list('question_text', flat=True))
    stale = _previously_asked_texts(getattr(session.resume, 'user', None))

    matched_topics = _matching_bank_topics(resume_text, skills)
    relevant_industries = detect_resume_industries(resume_text, skills)
    domain_qs = _domain_question_pool(is_it, relevant_industries)
    own_qs = domain_qs.filter(topic__in=matched_topics) if matched_topics else domain_qs.none()
    # Industry-scoped pool: the widen fallback stays on the candidate's domain.
    general_qs = domain_qs

    unlabelled = Q(difficulty__isnull=True) | Q(difficulty='')
    keys = DIFFICULTY_DB_KEYS.get(difficulty, DIFFICULTY_DB_KEYS['Easy'])

    # Most specific source first, widening only when a tier has nothing left -
    # the same fallback order generate_interview_questions() uses: the resume's
    # skills (least-asked skill first), then topics the resume mentions, then
    # its industries.
    skill_ids = _skill_question_ids(resume_text, skills, relevant_industries, is_it=is_it)
    asked = {}
    for s, ids in skill_ids.items():
        asked[s] = FAQQuestion.objects.filter(id__in=ids, question_text__in=seen).count()
    skill_tiers = []
    for s in sorted(skill_ids, key=lambda s: (asked[s], random.random())):
        pool = FAQQuestion.objects.filter(id__in=skill_ids[s])
        skill_tiers.append(pool.filter(Q(difficulty__in=keys) | unlabelled))
    skill_tiers += [FAQQuestion.objects.filter(id__in=sum(skill_ids.values(), []))]
    tiers = skill_tiers + [
        own_qs.filter(Q(difficulty__in=keys) | unlabelled),
        own_qs,
        general_qs.filter(Q(difficulty__in=keys) | unlabelled),
        general_qs,
    ]
    for tier in tiers:
        picked = _sample_questions(tier, 1, seen, stale)
        if picked:
            row = picked[0]
            return {
                'topic': row.topic.capitalize(),
                'difficulty': difficulty,
                'question': row.question_text,
                'question_type': 'theory',
                'candidate_type': candidate_type,
            }

    # Last resort: the same in-code fallback bank the batch path uses, for
    # an environment where the DB domain bank is unseeded or exhausted.
    fallback = (NON_IT_TECHNICAL_FALLBACK if not is_it else IT_TECHNICAL_FALLBACK)[:]
    random.shuffle(fallback)
    for text in fallback:
        if not _is_semantic_duplicate(text, seen):
            return {
                'topic': 'Domain',
                'difficulty': difficulty,
                'question': text,
                'question_type': 'theory',
                'candidate_type': candidate_type,
            }

    return None


def _top_up_from_bank(final_questions, bank, topic, target_len, seen, fresher=False):
    """Fill remaining slots from an in-code bank if the DB bank is short/unseeded.

    `fresher=True` applies the same employment filters the DB path uses. The
    in-code banks were exempt from them, so in an environment where the DB
    bank is unseeded or the filtered pool ran dry a fresher still got
    "How do you handle disagreements with your manager or team?" — the filters
    upstream were bypassed entirely by the safety net beneath them.
    """
    import random
    if len(final_questions) >= target_len:
        return
    pool = [q for q in bank if not _is_semantic_duplicate(q, seen)]
    if fresher:
        pool = [q for q in pool
                if not _is_senior_question(q)
                and not _ASSUMES_WORKPLACE_RE.search(q)
                and not _ASSUMES_JOB_RE.search(q)]
    random.shuffle(pool)
    for text in pool:
        if len(final_questions) >= target_len:
            break
        seen.add(text)
        final_questions.append({
            'topic': topic,
            'difficulty': 'Easy',
            'question': text,
            'question_type': 'theory',
        })


def extract_resume_skills(resume_text, extra_skills=None):
    """Concrete skills the resume actually evidences, for answer cross-checking.

    Scans the resume against the known tech-skill vocabulary and folds in any
    skills the analysis already matched. Deliberately does NOT include the fuzzy
    FAQ topic matches (which over-match on generic words) — this list is used to
    decide whether an answer's claims are backed by the resume, so it must only
    contain skills the resume genuinely shows.
    """
    low = (resume_text or '').lower()
    # len>=2 skips the single-letter 'r' (R language) matching any stray "R"
    # (initials, "R&D") and mislabelling it a skill.
    found = {s for s in _TECH_SKILLS if len(s) >= 2 and re.search(r'\b' + re.escape(s) + r'\b', low)}
    found |= {str(s).strip().lower() for s in (extra_skills or []) if str(s).strip()}
    return sorted(found)


# Topics with no textbook answer — scored on the candidate's own experience.
HR_TOPICS = ('behavioural', 'experience', 'academic/project')


def evaluate_answer(question, answer, topic=None, resume_context=None, spoken=False):
    """Score one interview answer 0-5 with a single LLM call.

    `spoken=True` (a speech transcript): the same call first recovers what the
    candidate MEANT — non-fluent speakers use slang, broken grammar and
    half-sentences, and speech-to-text mishears words ("sequel" for SQL) — and
    scores that. The result then carries `interpreted`, the cleaned-up answer.
    """
    topic_line = f"\nQuestion Topic / Skill: {topic}\n" if topic else ""

    resume_block = ""
    consistency_rule = ""
    if resume_context:
        skills = ', '.join(resume_context.get('skills') or []) or 'none listed'
        years = resume_context.get('years')
        years_str = (f"{years:g} year(s)" if years else "fresher / not stated")
        ctype = resume_context.get('candidate_type') or 'unknown'
        domain = ', '.join(resume_context.get('domain') or []) or 'not identified'
        resume_block = (
            "\nCANDIDATE RESUME PROFILE (the interview validates THIS resume):\n"
            f"- Resume skills: {skills}\n"
            f"- Domain / industry: {domain}\n"
            f"- Experience on resume: {years_str}\n"
            f"- Candidate type: {ctype}\n"
        )
        consistency_rule = (
            "\nRESUME CONSISTENCY CHECK (apply after the relevance gate):\n"
            "- The candidate should answer from the skills/experience on their RESUME.\n"
            "- Only claims that CLEARLY CONTRADICT the resume profile count as unverified: a\n"
            "  different field of work entirely (a Civil-Engineering resume whose answer\n"
            "  describes production Python/Django/LLM work), or a seniority the resume rules\n"
            "  out (a fresher describing years of production ownership). Such an answer scores\n"
            "  at most 3/5 and the feedback must say the claim is not backed by the resume.\n"
            "- A resume lists highlights, not everything. Tools, libraries, tasks or side\n"
            "  projects that are NOT on the resume but are normal for the candidate's field and\n"
            "  level are plausible: do NOT treat them as fabricated and do NOT deduct for them.\n"
            "- An answer consistent with the resume profile is scored normally.\n"
        )

    # Behavioural / experience / academic questions have no "correct" answer to
    # check, so relevance means a concrete personal example that fits the resume.
    hr_rule = ""
    if (topic or '').strip().lower() in HR_TOPICS:
        hr_rule = (
            "\nBEHAVIOURAL / EXPERIENCE QUESTION RULES (these REPLACE the rubric below):\n"
            "- There is no textbook answer. Score ONLY on which of these components the\n"
            "  candidate actually gives:\n"
            "    S (situation) - a specific, real situation from their own past: a particular\n"
            "        time, place, project, task or event. NOT how they generally behave.\n"
            "    A (action)    - what THEY personally did in that situation (not the team,\n"
            "        not the company, not what should be done in general).\n"
            "    R (result)    - how it turned out. Nice to have, but it does NOT change the\n"
            "        score: an answer with S and A scores 5 whether or not R is there.\n"
            "- Relevance gate for these questions: the answer passes if it is about the KIND of\n"
            "  situation the question asks about. A different-but-related story, or one told out\n"
            "  of order, still passes - only a completely unrelated answer scores 0.\n"
            "- STEP: decide which of S and A are present, then award:\n"
            "    5 - S + A: a specific situation AND what they personally did in it.\n"
            "    4 - S only: the situation is there, but no clear action of their own (they set\n"
            "        the scene and stop, or describe only what the team/others did).\n"
            "    3 - No specific situation: their own usual practice (\"I usually handle it\n"
            "        by...\", \"normally I...\") OR a hypothetical answer that still describes\n"
            "        concrete actions they would take.\n"
            "    2 - Platitudes or opinions with no example (\"teamwork is important\", \"I always\n"
            "        communicate well\"); a fragment; or an on-topic answer carrying none of\n"
            "        S, A or R.\n"
            "    1 - On topic but says nothing gradable: the question restated in their own\n"
            "        words, or a bare acknowledgement (\"yes, I have done that\", \"it was fine\")\n"
            "        with no content behind it.\n"
            "    0 - Nothing gradable at all: blank, \"I don't know\", a refusal, a completely\n"
            "        different subject, or the question read back word for word.\n"
            "- Award the HIGHEST score whose components are all present. Do not add or remove\n"
            "  points for anything outside S and A.\n"
            "- A fresher's examples from college projects, internships, coursework, clubs,\n"
            "  part-time work or personal life count exactly the same as workplace examples.\n"
            "- NEVER deduct for: plain or informal language, a short answer, a small-scale or\n"
            "  ordinary story, a missing result, missing STAR wording, missing numbers, missing\n"
            "  job titles or dates.\n"
            "- NEVER award for: polish, confidence, rehearsed delivery or length.\n"
        )

    interpret_step = ""
    interpreted_field = ""
    if spoken:
        interpret_step = (
            "\nSTEP 1 - UNDERSTAND THE SPOKEN ANSWER (the Candidate Answer is a raw speech transcript):\n"
            "- The candidate may not speak English fluently: expect broken grammar, slang, filler\n"
            "  words, repetition and half-finished sentences, and speech-to-text may have misheard\n"
            "  words (e.g. \"sequel\" for \"SQL\", \"topple\" for \"tuple\", \"jungle\" for \"Django\").\n"
            "- Work out what the candidate MEANT, using the question as context, and write it as\n"
            "  \"interpreted_answer\" in clear, simple, first-person English.\n"
            "- Keep ONLY the candidate's own points. Do NOT add facts, steps, examples or terms they\n"
            "  did not say or clearly mean, and do NOT make a wrong or vague answer better.\n"
            "- Leave out parts with no discernible meaning.\n"
            "Then score the interpreted answer (STEP 2 below).\n"
        )
        interpreted_field = '    "interpreted_answer": "what the candidate meant, in clear English",\n'

    prompt = f"""
You are an expert interview evaluator.

Evaluate the candidate's answer ONLY based on whether it correctly answers the interview question.
{topic_line}{resume_block}{hr_rule}
Question:
{question}

Candidate Answer:
{answer}
{interpret_step}
JUDGE MEANING, NOT LANGUAGE:
- Score the IDEAS the candidate conveys. Grammar, fluency, accent, word choice, filler words,
  repetition and sentences that stop mid-way MUST NOT reduce the score.
- An answer that was cut off mid-way is scored on what it conveyed before it stopped.
- A short, informal answer that gets the core idea right is a correct answer: do not deduct
  for missing extra details, examples or depth the question did not ask for.

RELEVANCE GATE (apply FIRST, before any other scoring):
- The answer MUST be strictly relevant to the Question{" and to the Question Topic / Skill above" if topic else ""}.
- If the answer is off-topic, about a different subject/skill, generic filler,
  evasive, blank, "I don't know", or does not actually address what the
  question asks, the score is 0. No partial credit for fluent-but-irrelevant text.
- A well-written answer to a DIFFERENT question still scores 0.
Only if the answer passes this gate, apply the rubric below.
{consistency_rule}

SCORING RULES — follow them in this order. The score is decided by the tests below, not by
how the answer sounds.

STEP A - establish two facts about the answer:
  CORRECTNESS: of what the candidate actually said, is it right? (all right / one small thing
               wrong / mixed / mostly wrong / all wrong)
  COVERAGE:    how much of what the question asked has been addressed? (all / most / part /
               almost none)

STEP B - the DEPTH CONDITION. It is met when the answer, on top of being correct, does at
least ONE of these, correctly:
  (a) gives a concrete example, use case or situation where this applies;
  (b) explains WHY / how it works underneath, not only what it is;
  (c) states a trade-off, limitation, comparison, or when NOT to use it;
  (d) adds a specific technical detail that shows real hands-on use (a command, a parameter,
      a performance or cost consequence, an edge case, a mistake people make).
Depth stated wrongly does NOT meet the condition.

STEP C - award the FIRST score whose test passes, reading from 5 down:

5/5 - CORRECTNESS = all right, COVERAGE = all, AND the DEPTH CONDITION is met.
      This is the only way to score 5.

4/5 - CORRECTNESS = all right (or one small thing wrong) and COVERAGE = all or most,
      but no depth. The plain, correct, to-the-point answer lives here.
      A correct answer stays at 4 no matter how short, informal or unpolished it is.

3/5 - The candidate is right about what they did say, but COVERAGE = part: they answered
      one side of a two-sided question, defined the term but not the behaviour asked about,
      or stopped before the part the question actually turns on.
      Also 3 when COVERAGE = all but one clear, material error sits in the answer.

2/5 - The answer is on the right subject but the key concept is missing or stated wrongly:
      more of it is wrong than right, or it describes something adjacent to what was asked.
      A real attempt, not a non-answer.

1/5 - Only a fragment connects to the question — a correct keyword inside otherwise wrong or
      empty content, or a vague gesture at the topic with no substance.

0/5 - Any of: fails the RELEVANCE GATE; blank; "I don't know"; the question repeated, read
      aloud or rephrased with no answer; a fluent answer to a DIFFERENT question; content
      with nothing that addresses what was asked.

TIE-BREAK: if an answer sits between two scores, give the LOWER one — except that the
DEPTH CONDITION, when met, is what lifts 4 to 5.

NEVER deduct for: grammar, accent, fluency, filler words, informal wording, short length,
a different-but-valid explanation, or the answer not matching a textbook wording.
NEVER award for: confidence, polish, rehearsed delivery, length, or repeating the question's
own words back.

Return ONLY valid JSON:

{{
{interpreted_field}    "score": 5,
    "feedback": "Explain in one or two sentences why this score was awarded."
}}
"""
    # temperature=0 — scoring must be deterministic and obey the RELEVANCE
    # GATE. At the previous default (0.7) the model drifted and handed out
    # 5/5 to off-topic answers (e.g. an AI answer to a Civil-Engineering
    # question), because the sampling noise overrode the strict rubric.
    # Every answer MUST come back with a real score and normal feedback — the
    # candidate never sees an error or an "could not evaluate" message.
    #   1. the full prompt, twice (broken JSON is salvaged by _parse_evaluation);
    #   2. a short score-only prompt, which a struggling model gets right more often;
    #   3. a local relevance scorer, if the AI service is down or unusable.
    # Each call has a short timeout and the whole ladder a time budget, so a
    # hanging AI service cannot leave the candidate waiting.
    import time
    deadline = time.monotonic() + EVALUATION_TIME_BUDGET_SECONDS
    compact = _compact_evaluation_prompt(question, answer, topic, resume_context, spoken)
    result = None
    for attempt, attempt_prompt in enumerate((prompt, prompt, compact, compact), 1):
        remaining = deadline - time.monotonic()
        if remaining < 3:
            break
        try:
            raw = _sarvam_chat(attempt_prompt, temperature=0,
                               timeout=min(15, remaining), max_retries=1)
        except Exception as e:
            logger.error(f"Answer evaluation call failed (attempt {attempt}): {e}")
            time.sleep(min(0.5 * attempt, max(0, deadline - time.monotonic() - 3)))
            continue
        result = _parse_evaluation(raw)
        if result is not None:
            break
        logger.warning(f"Unparseable evaluation response (attempt {attempt}): {str(raw)[:1000]!r}")
    if result is None:
        logger.error("AI evaluation unavailable — answer scored by the local relevance scorer.")
        return _local_answer_score(question, answer, topic, resume_context)

    try:
        result.setdefault('feedback', '')
        if spoken:
            interpreted = str(result.pop('interpreted_answer', '') or '').strip()
            # A rewrite several times longer than what was said has added content.
            if interpreted and len(interpreted.split()) <= max(40, 2 * len(str(answer).split())):
                result['interpreted'] = interpreted
        # Clamp to the 0-5 range (each question carries 5 marks)
        try:
            result['score'] = max(0, min(5, round(float(result.get('score', 0)))))
        except (ValueError, TypeError):
            result['score'] = 0
        if not str(result.get('feedback') or '').strip():
            result['feedback'] = _local_answer_score(question, answer, topic, resume_context)['feedback']
        return result
    except Exception as e:
        logger.error(f"Answer evaluation post-processing failed: {e}")
        return _local_answer_score(question, answer, topic, resume_context)


# Upper bound on how long scoring one answer may take before the local scorer
# takes over (see evaluate_answer).
EVALUATION_TIME_BUDGET_SECONDS = 25


def _compact_evaluation_prompt(question, answer, topic, resume_context, spoken):
    """A much shorter version of the evaluation prompt, used when the full one
    keeps failing. Same scale and core rules, minimal output."""
    skills = ', '.join((resume_context or {}).get('skills') or []) or 'not listed'
    interpreted = '"interpreted_answer": "<what the candidate meant, clear English>", ' if spoken else ''
    hr = str(topic or '').strip().lower() in HR_TOPICS
    rules = (
        """Rules: behavioural/experience question, no textbook answer. Score ONLY on two
components: S = a specific real situation from their own past (not how they usually behave),
A = what THEY personally did in it. A result is nice to have but never changes the score.
5 = S + A
4 = S only — the situation is there but no clear action of their own
3 = no specific situation: their usual practice ("I usually handle it by...") or a
    hypothetical with concrete actions
2 = platitudes or opinions with no example, a fragment, or an on-topic answer with none
    of S, A or R
1 = on topic but nothing gradable: the question restated, or a bare acknowledgement
    ("yes, I have done that") with no content
0 = nothing gradable: blank, "I don't know", a refusal, a completely different subject,
    or the question read back word for word
College, internship and personal examples count fully. Never deduct for plain language, a
short answer, a missing result or a small-scale story; never award for polish or length.
Only a claim that clearly contradicts the resume caps it at 3."""
        if hr else
        """Rules: judge the meaning, not grammar or fluency. Award the first that fits, from 5 down:
5 = fully correct, covers everything asked, AND adds depth — an example, why it works, a
    trade-off/limitation, or a hands-on detail (stated correctly)
4 = correct and covers what was asked, but no depth — the normal score for a good answer
3 = right about what it says but answers only part of the question, or one clear error in it
2 = right subject, key concept missing or wrong
1 = only a fragment relates to the question
0 = wrong, off-topic, blank, "I don't know", or the question repeated back
Between two scores pick the lower. Never deduct for grammar, fluency or short length; never
award for confidence, polish or length. A claim that clearly contradicts the resume caps it at 3."""
    )
    return f"""Score this interview answer from 0 to 5.

Question: {question}
Topic: {topic or 'general'}
Candidate resume skills: {skills}
Answer (may be spoken, with broken grammar or cut off): {answer}

{rules}

Reply with ONE line of JSON and nothing else:
{{{interpreted}"score": <0-5>, "feedback": "<one or two sentences to the candidate>"}}"""


def _local_hr_answer_score(answer):
    """Local S/A score for a behavioural / experience answer (AI service down).

    These questions have no key vocabulary to match - an answer about a real
    situation rarely repeats the question's words - so keyword coverage scored
    every genuine story a 2. This looks for the same components the LLM prompt
    scores on:

        S  a specific past situation of the candidate's own
        A  what they personally did in it

    A result is not scored. Coarse by nature: it only runs when the AI service
    is unreachable.
    """
    # The raw answer, not a filtered word list: filtering drops one-letter
    # tokens, which would throw away every "I".
    text = str(answer or '').lower().strip()
    n = len(text.split())

    # Nothing gradable at all -> 0, before anything else is looked at.
    refusal = bool(re.match(
        r"^(no idea|i (?:really )?(?:don'?t|do not) know|don'?t know|not sure|"
        r"no comment|skip|pass|nothing|n/?a)\b", text))
    if not text or refusal or n < 3:
        return {'score': 0, 'feedback': 'No answer was given to this question. '
                                        'Describe a real situation from your own experience.'}

    personal = bool(re.search(r'\b(i|we|my|our|me|us)\b', text))
    past_action = bool(re.search(
        r'\b\w{3,}ed\b|\b(did|made|built|led|took|ran|wrote|gave|went|had|got|spoke|'
        r'chose|kept|met|set|told|helped|fixed|solved|handled|managed|created|organised|'
        r'organized|learnt|learned|worked|tested|delivered|presented|spent|sat|rang|'
        r'called|asked|checked|split|rewrote|stayed)\b', text))
    setting = bool(re.search(
        r'\b(project|team|client|customer|college|university|internship|intern|manager|'
        r'lead|deadline|exam|assignment|semester|company|office|class|professor|lecturer|'
        r'bug|issue|ticket|task|hackathon|event|shift|report|presentation|audit|'
        r'inspection|site|machine|patient|order|invoice|campaign)\b', text))
    # "Once", "last year", "during my internship" - markers of one particular
    # occasion rather than a general habit.
    occasion = bool(re.search(
        r'\b(once|one time|last (?:year|month|week|semester|sem)|during (?:my|the)|'
        r'in my (?:final|first|second|third|last)|there was a|we had a|i had a|'
        r'at that time|that day|back (?:then|when))\b', text))
    habitual = bool(re.search(
        r"\b(usually|normally|generally|always|whenever|typically|i tend to|"
        r"my approach is|i would|i'd|i will|if (?:i|it|there))\b", text))
    # A bare acknowledgement: on topic, but no content behind it.
    bare = bool(re.match(
        r"^(yes|yeah|yep|no|sure|of course|definitely|i have|i did|it was|that'?s right)"
        r"[\s,.!-]*(i have done that|i did that|done that|it was fine|fine|good|ok(?:ay)?)?[\s.!]*$",
        text))

    # S needs a real occasion, not just a topic word: "I am a good team player"
    # mentions a team but tells no story, and "I usually check twice" is a habit.
    has_s = personal and setting and (occasion or past_action) and not (habitual and not occasion)
    has_a = has_s and past_action

    if has_a and n >= 12:
        return {'score': 5, 'feedback': 'You give a specific situation and what you personally '
                                        'did in it - a complete answer.'}
    if has_s and n >= 10:
        return {'score': 4, 'feedback': 'You set the situation out clearly. Say what YOU '
                                        'personally did in it to reach full marks.'}
    if personal and habitual and n >= 10:
        return {'score': 3, 'feedback': 'This is your general approach rather than one real '
                                        'example. Pick a specific time it happened and walk through it.'}
    if bare or n < 6:
        return {'score': 1, 'feedback': 'Your answer does not say anything the interviewer can '
                                        'judge. Describe a specific situation you were in.'}
    return {'score': 2, 'feedback': 'Your answer gives an opinion but no experience to back it. '
                                    'Describe a specific situation you were actually in.'}


def _local_answer_score(question, answer, topic=None, resume_context=None):
    """Score an answer without the AI service: how much of the question's (and
    topic's) key vocabulary the answer covers, and how substantial it is. Only
    used when the AI cannot be reached — it is coarse, but it always returns a
    real score with ordinary feedback, never an error."""
    answer_words = [w for w in re.findall(r'[a-zA-Z][a-zA-Z0-9+#]*', str(answer or '')) if len(w) > 1]
    if len(answer_words) < 5:
        return {'score': 0, 'feedback': 'The answer is too brief to address the question. '
                                        'Explain your answer in a few complete points.'}

    if str(topic or '').strip().lower() in HR_TOPICS:
        return _local_hr_answer_score(answer)

    answer_kw = _question_keywords(' '.join(answer_words))
    target_kw = set(_question_keywords(str(question or '')))
    if topic:
        target_kw |= _question_keywords(str(topic))
    skills_kw = _question_keywords(' '.join((resume_context or {}).get('skills') or []))

    coverage = len(answer_kw & target_kw) / max(1, len(target_kw))
    grounded = bool(answer_kw & skills_kw)
    substantial = len(answer_words) >= 25
    # 5 is reserved for a correct answer that also went deeper (see the DEPTH
    # CONDITION in the prompt). Locally the only proxy is a much fuller answer.
    in_depth = len(answer_words) >= 45

    if coverage >= 0.5 and in_depth:
        score = 5
    elif coverage >= 0.5 or (coverage >= 0.3 and substantial):
        score = 4
    elif coverage >= 0.3 or (coverage > 0 and substantial):
        score = 3
    elif coverage > 0:
        score = 2
    elif grounded and substantial:
        score = 1
    else:
        score = 0
    feedback = {
        5: 'Your answer addresses the question directly and covers what it asks for.',
        4: 'Your answer addresses the question directly and covers its key points. '
           'A specific example from your own work would make it even stronger.',
        3: 'Your answer is on the right track and addresses part of the question. '
           'Cover the remaining points and support them with a concrete example.',
        2: 'Your answer touches on the question but misses most of what it asks. '
           'Focus on the core concept and explain it step by step.',
        1: 'Your answer only loosely relates to the question. '
           'Address what the question asks directly before adding background.',
        0: 'Your answer does not address the question that was asked. '
           'Listen to the question carefully and answer it directly.',
    }[score]
    return {'score': score, 'feedback': feedback}


def _parse_evaluation(raw):
    """The {score, feedback, interpreted_answer} dict from an evaluation reply,
    or None if not even a score can be recovered. Falls back to pulling the
    fields out with regexes when the JSON itself is broken (truncated, stray
    quotes, prose around it)."""
    try:
        result = _parse_json_response(raw)
        if isinstance(result, list) and result:
            result = result[0]
        if isinstance(result, dict) and 'score' in result:
            return result
    except ValueError:
        pass

    text = str(raw or '')
    score = re.search(r'"?score"?\s*[:=]\s*"?(\d(?:\.\d+)?)', text, re.IGNORECASE)
    if not score:
        return None

    def _field(name):
        # Tolerates an unterminated string when the reply was cut off.
        m = re.search(r'"' + name + r'"\s*:\s*"((?:[^"\\]|\\.)*)', text, re.IGNORECASE)
        return m.group(1).replace('\\"', '"').replace('\\n', ' ').strip() if m else ''

    return {
        'score': score.group(1),
        'feedback': _field('feedback'),
        'interpreted_answer': _field('interpreted_answer'),
    }


def validate_resume_fields(text):
    """
    Validates if a resume contains at least 3 out of 10 standard fields.
    Returns (is_valid, matched_count, matched_fields, missing_fields).
    """
    import re
    if not text:
        return False, 0, [], []
    
    text_lower = text.lower()
    
    fields = {
        "Name & Contact Information": False,
        "Professional Summary / Career Objective": False,
        "Technical Skills": False,
        "Work Experience": False,
        "Projects": False,
        "Education": False,
        "Certifications": False,
        "Achievements / Awards": False,
        "Languages": False,
        "Additional Information": False,
    }

    # 1. Name & Contact (Look for email and phone)
    has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text))
    has_phone = bool(re.search(r'\+?\d{10,12}', text))
    if has_email and has_phone:
        fields["Name & Contact Information"] = True
    
    # Check section headers (naive but fast heuristic)
    if re.search(r'\b(professional summary|career objective|about me|profile|summary)\b', text_lower):
        fields["Professional Summary / Career Objective"] = True
    
    if re.search(r'\b(technical skills|skills|core competencies|technologies)\b', text_lower):
        fields["Technical Skills"] = True
        
    if re.search(r'\b(work experience|experience|employment history|professional experience)\b', text_lower):
        fields["Work Experience"] = True
        
    if re.search(r'\b(projects|academic projects|personal projects)\b', text_lower):
        fields["Projects"] = True
        
    if re.search(r'\b(education|academic background|qualifications)\b', text_lower):
        fields["Education"] = True
        
    if re.search(r'\b(certifications|certificates|courses)\b', text_lower):
        fields["Certifications"] = True
        
    if re.search(r'\b(achievements|awards|honors)\b', text_lower):
        fields["Achievements / Awards"] = True
        
    if re.search(r'\b(languages)\b', text_lower):
        fields["Languages"] = True
        
    if re.search(r'\b(additional information|activities|interests|hobbies)\b', text_lower):
        fields["Additional Information"] = True

    matched = [k for k, v in fields.items() if v]
    missing = [k for k, v in fields.items() if not v]
    
    return len(matched) >= 3, len(matched), matched, missing
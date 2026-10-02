"""Experience-level fit: a fresher must not be asked about a career they have
not had, and an experienced candidate must not be asked student questions.

Run:  python manage.py test career_app.tests_level_fit
"""
import re

from django.test import SimpleTestCase

from career_app import resume_utils as ru


# Wording that only makes sense to someone who has HELD A JOB.
WORKPLACE_MARKERS = re.compile(
    r"\b(your boss|the boss|your manager|senior leadership|senior management|"
    r"stakeholders?|colleagues?|co-?workers?|performance review|promotions?|"
    r"direct reports?|your company|your employer|the client|clients|"
    r"your organi[sz]ation|headcount|layoffs?|p&l|cultural fit|"
    r"previous (?:job|role|employer)|in your current role|at work)\b",
    re.IGNORECASE,
)

# Wording that only makes sense to someone STILL STUDYING / just out of college.
STUDENT_MARKERS = re.compile(
    r"\b(your (?:college|university|school)|final year project|coursework|"
    r"your professor|your lecturer|your syllabus|semester|classmates?|"
    r"campus placement|your degree|during your studies|as a student)\b",
    re.IGNORECASE,
)

FRESHER_RESUME = (
    'B.Com graduate seeking an entry-level opportunity in HR, administration or '
    'operations. Fresher - no prior full-time experience. MS Word, MS Excel, '
    'Email Communication, Documentation, Data Entry, Teamwork. College Project: '
    'Employee Attendance and Leave Tracking - an Excel-based tracker.'
)

EXPERIENCED_RESUME = (
    'Senior HR Business Partner with 8 years of experience across manufacturing '
    'and shared services. Led hiring for 200+ roles, managed stakeholder '
    'relationships, ran performance review cycles, handled employee relations, '
    'headcount planning and workforce budgeting.'
)

HR_TOPICS = ('Behavioural', 'Experience', 'Academic/Project')


def _paper(resume_text):
    """One generated interview, split into its HR and technical halves."""
    questions = ru.generate_interview_questions(
        resume_text, '', skills=[], user=None, domain_count=10
    )
    hr = [q for q in questions if q['topic'] in HR_TOPICS]
    technical = [q for q in questions if q['topic'] not in HR_TOPICS]
    return questions, hr, technical


class FresherGetsNoExperiencedQuestionsTests(SimpleTestCase):
    databases = {'default'}
    RUNS = 4

    def test_hr_block_has_no_workplace_questions(self):
        offenders = []
        for _ in range(self.RUNS):
            _all, hr, _tech = _paper(FRESHER_RESUME)
            offenders += [q['question'] for q in hr if WORKPLACE_MARKERS.search(q['question'])]
        self.assertEqual(offenders, [], f'fresher asked about a job they never had: {offenders[:3]}')

    def test_hr_block_has_no_senior_questions(self):
        offenders = []
        for _ in range(self.RUNS):
            _all, hr, _tech = _paper(FRESHER_RESUME)
            offenders += [q['question'] for q in hr if ru._is_senior_question(q['question'])]
        self.assertEqual(offenders, [], f'fresher asked a manager question: {offenders[:3]}')

    def test_technical_block_has_no_workplace_questions(self):
        offenders = []
        for _ in range(self.RUNS):
            _all, _hr, tech = _paper(FRESHER_RESUME)
            offenders += [q['question'] for q in tech if WORKPLACE_MARKERS.search(q['question'])]
        self.assertEqual(offenders, [], f'fresher technical block assumes a job: {offenders[:3]}')

    def test_fresher_block_is_academic_not_experience(self):
        _all, hr, _tech = _paper(FRESHER_RESUME)
        topics = {q['topic'] for q in hr}
        self.assertIn('Academic/Project', topics)
        self.assertNotIn('Experience', topics,
                         'a fresher must get the academic block, never the experience block')


class ExperiencedGetsNoFresherQuestionsTests(SimpleTestCase):
    databases = {'default'}
    RUNS = 4

    def test_hr_block_has_no_student_questions(self):
        offenders = []
        for _ in range(self.RUNS):
            _all, hr, _tech = _paper(EXPERIENCED_RESUME)
            offenders += [q['question'] for q in hr if STUDENT_MARKERS.search(q['question'])]
        self.assertEqual(offenders, [], f'experienced candidate asked a student question: {offenders[:3]}')

    def test_technical_block_has_no_student_questions(self):
        offenders = []
        for _ in range(self.RUNS):
            _all, _hr, tech = _paper(EXPERIENCED_RESUME)
            offenders += [q['question'] for q in tech if STUDENT_MARKERS.search(q['question'])]
        self.assertEqual(offenders, [], f'experienced technical block is student-pitched: {offenders[:3]}')

    def test_experience_block_is_used_not_academic(self):
        _all, hr, _tech = _paper(EXPERIENCED_RESUME)
        topics = {q['topic'] for q in hr}
        self.assertIn('Experience', topics)
        self.assertNotIn('Academic/Project', topics,
                         'an experienced candidate must get the experience block')


class TechnicalDifficultyMixTests(SimpleTestCase):
    """The technical block's difficulty is calibrated to years: a fresher's ten
    questions lean Easy, an experienced candidate's lean Hard."""

    databases = {'default'}

    def _difficulty_labels(self, resume_text):
        from career_app.models import FAQQuestion
        _all, _hr, tech = _paper(resume_text)
        tiers = []
        for question in tech:
            row = FAQQuestion.objects.filter(question_text=question['question']).first()
            if row and row.difficulty:
                for tier, keys in ru.DIFFICULTY_DB_KEYS.items():
                    if row.difficulty in keys:
                        tiers.append(tier)
                        break
        return tiers

    def test_fresher_leans_easy(self):
        tiers = self._difficulty_labels(FRESHER_RESUME)
        if not tiers:
            self.skipTest('question bank not seeded in this environment')
        self.assertGreater(tiers.count('Easy'), tiers.count('Hard'),
                           f'fresher technical block should lean Easy, got {tiers}')

    def test_experienced_leans_hard(self):
        tiers = self._difficulty_labels(EXPERIENCED_RESUME)
        if not tiers:
            self.skipTest('question bank not seeded in this environment')
        self.assertGreaterEqual(tiers.count('Hard') + tiers.count('Intermediate'),
                                tiers.count('Easy'),
                                f'experienced technical block should not lean Easy, got {tiers}')

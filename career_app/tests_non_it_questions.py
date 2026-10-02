"""A non-IT candidate must never be served software/IT domain questions.

Run:  python manage.py test career_app.tests_non_it_questions
"""
from django.test import SimpleTestCase, TestCase

from career_app import resume_utils as ru
from career_app.models import FAQQuestion


COMMERCE = 'B.Com graduate. Skills: MS Excel, Tally, SQL basics, communication.'
HR = 'HR executive. Recruitment, payroll, MS Office, basic HTML for job posts.'
CIVIL = 'Civil engineer. AutoCAD, STAAD Pro, quantity surveying, site supervision.'
DEV = 'Software engineer. Python, Django, REST APIs, PostgreSQL.'


class ITProfileClassificationTests(SimpleTestCase):
    """SQL/HTML on a non-IT resume is a tool, not a software career."""

    def test_sql_alone_does_not_make_a_commerce_resume_it(self):
        self.assertFalse(ru._is_it_profile(COMMERCE, []))

    def test_html_alone_does_not_make_an_hr_resume_it(self):
        self.assertFalse(ru._is_it_profile(HR, []))

    def test_core_engineering_resume_is_not_it(self):
        self.assertFalse(ru._is_it_profile(CIVIL, []))

    def test_two_data_tools_together_still_count_as_it(self):
        self.assertTrue(ru._is_it_profile('Data analyst. SQL, MongoDB dashboards.', []))

    def test_a_real_developer_is_still_it(self):
        self.assertTrue(ru._is_it_profile(DEV, []))


class DomainPoolGateTests(TestCase):
    """The IT exclusion lives on the pool, so an empty industry list cannot
    reopen the whole bank — that was how SQL questions reached non-IT papers."""

    @classmethod
    def setUpTestData(cls):
        FAQQuestion.objects.create(
            topic='sql joins', industry='it & software', difficulty='easy',
            question_text='What is the difference between an INNER JOIN and a LEFT JOIN?')
        FAQQuestion.objects.create(
            topic='quantity surveying', industry='construction & civil', difficulty='easy',
            question_text='How do you prepare a bill of quantities?')

    def test_no_industries_detected_still_excludes_it_for_a_non_it_profile(self):
        topics = list(ru._domain_question_pool(False, []).values_list('topic', flat=True))
        self.assertNotIn('sql joins', topics)
        self.assertIn('quantity surveying', topics)

    def test_an_it_profile_keeps_the_it_questions(self):
        topics = list(ru._domain_question_pool(True, []).values_list('topic', flat=True))
        self.assertIn('sql joins', topics)

    def test_industry_filter_and_it_gate_apply_together(self):
        topics = list(
            ru._domain_question_pool(False, ['construction & civil'])
            .values_list('topic', flat=True))
        self.assertEqual(topics, ['quantity surveying'])


class SkillMatchGateTests(TestCase):
    """A skill with no questions in the candidate's own industries falls back to
    other industries — that fallback must not reach the IT bank for a non-IT
    candidate."""

    @classmethod
    def setUpTestData(cls):
        FAQQuestion.objects.create(
            topic='sql queries', industry='it & software', difficulty='easy',
            question_text='Write a SQL query to find duplicate rows in a table.')

    def setUp(self):
        # The bank index is an in-memory cache keyed by time, not by content.
        ru._BANK_INDEX['built_at'] = None

    def test_sql_skill_on_a_non_it_resume_matches_nothing(self):
        ids = ru._skill_question_ids(COMMERCE, ['sql'], ['banking & finance'], is_it=False)
        self.assertEqual(ids.get('sql', []), [])

    def test_sql_skill_on_an_it_resume_still_matches(self):
        ids = ru._skill_question_ids(DEV, ['sql'], ['it & software'], is_it=True)
        self.assertTrue(ids.get('sql'))


class GenericWordLeakTests(TestCase):
    """A word that lives in every industry's topic names must not decide the
    candidate's department. "Documentation" on a B.Com admin resume was voting
    for 'engineering & heavy industries' and produced an engineering-drawing
    question in a real interview."""

    # A miniature bank: each industry gets topics whose wording mirrors the
    # real sheets, including the generic words that caused the collision.
    BANK = {
        'engineering & heavy industries': [
            'engineering drawing and documentation', 'welding procedures',
            'gearbox assembly', 'machine maintenance documentation'],
        'manufacturing & advanced mfg.': [
            'cnc machining', 'lean manufacturing', 'production documentation'],
        'infrastructure & construction': [
            'concrete technology', 'site supervision', 'site documentation'],
        'refinery & petrochemical': [
            'distillation column operation', 'pipeline inspection documentation'],
        'warehousing & industrial logistics': [
            'inventory cycle counting', 'e-commerce order fulfilment',
            'dispatch documentation'],
        'non-voice process': [
            'email support', 'back office', 'data entry accuracy',
            'office documentation'],
        'workforce outsourcing & managed staffing': [
            'payroll administration', 'contract staffing administration',
            'vendor documentation'],
    }

    COMMERCE_ADMIN = (
        'B.Com graduate seeking an entry-level opportunity in HR, administration '
        'or operations. MS Word, MS Excel, PowerPoint, Email Communication, '
        'Documentation, Data Entry, Teamwork, Time Management, Basic HR & Administration. '
        'College Project: Employee Attendance and Leave Tracking - an Excel-based tracker. '
        'CERTIFICATIONS MS Office Fundamentals. Declaration: the information above is true.'
    )
    MECHANICAL = (
        'B.E Mechanical Engineer. SolidWorks, AutoCAD, CNC machining, GD&T, welding, '
        'sheet metal, thermodynamics, ANSYS, lean manufacturing, machine maintenance.'
    )

    @classmethod
    def setUpTestData(cls):
        for industry, topics in cls.BANK.items():
            for topic in topics:
                FAQQuestion.objects.create(
                    topic=topic, industry=industry, difficulty='easy',
                    question_text=f'What is {topic}?')

    def test_office_words_do_not_elect_an_engineering_industry(self):
        industries = ru.detect_resume_industries(self.COMMERCE_ADMIN, [])
        for banned in ('engineering & heavy industries', 'manufacturing & advanced mfg.',
                       'refinery & petrochemical', 'warehousing & industrial logistics',
                       'infrastructure & construction'):
            self.assertNotIn(banned, industries, f'{banned} reached an admin resume')

    def test_admin_resume_lands_in_an_office_industry(self):
        industries = ru.detect_resume_industries(self.COMMERCE_ADMIN, [])
        self.assertTrue(industries, 'a thin admin resume must still get a department')
        self.assertTrue(
            any('process' in i or 'workforce' in i or 'staffing' in i for i in industries),
            f'expected a back-office/staffing industry, got {industries}')

    def test_a_real_engineer_still_reaches_engineering(self):
        industries = ru.detect_resume_industries(self.MECHANICAL, [])
        self.assertTrue(
            any('manufactur' in i or 'engineering' in i for i in industries),
            f'mechanical resume must keep its industries, got {industries}')


class SkillMatchStaysInDepartmentTests(TestCase):
    """A skill that matches rows in another department is a word collision, not
    a signal — once the candidate's industries are known it must be dropped."""

    @classmethod
    def setUpTestData(cls):
        FAQQuestion.objects.create(
            topic='engineering drawing and documentation',
            industry='engineering & heavy industries', difficulty='easy',
            question_text='How would you explain engineering drawing and documentation?')

    def setUp(self):
        ru._BANK_INDEX['built_at'] = None

    def test_documentation_skill_does_not_cross_into_engineering(self):
        ids = ru._skill_question_ids(
            'B.Com admin fresher with documentation and data entry skills.',
            ['documentation'], ['non-voice process'], is_it=False)
        self.assertEqual(ids.get('documentation', []), [])

    def test_fallback_still_applies_when_no_industry_is_known(self):
        ids = ru._skill_question_ids(
            'Documentation specialist.', ['documentation'], [], is_it=False)
        self.assertTrue(ids.get('documentation'),
                        'with no industry detected, any on-skill question beats none')


class FresherHRBlockTests(TestCase):
    """A fresher has no boss, no stakeholders, no colleagues and no performance
    review. Those questions were reaching the Behavioural and Academic blocks,
    which filtered for SENIORITY only — not for having held a job at all."""

    FRESHER = (
        'B.Com graduate seeking an entry-level opportunity in HR or administration. '
        'Fresher - no prior full-time experience. College project: Excel attendance tracker.'
    )

    WORKPLACE_ONLY = [
        "Tell me about a time you disagreed with your boss's approach but still had to deliver.",
        'Describe a time you had a conflict with a coworker and how you resolved it.',
        "Describe how you've built trust with a skeptical stakeholder.",
        'Tell me about a time a mistake of yours was visible to senior leadership.',
        'Describe a time you improved a performance review process.',
        'How do you evaluate cultural fit versus skill fit?',
    ]
    FRESHER_SAFE = [
        'Tell me about a time you worked in a college project team.',
        'Describe a deadline for an assignment you nearly missed.',
        'What did you learn from your final year project?',
    ]

    def test_workplace_questions_are_recognised(self):
        for question in self.WORKPLACE_ONLY:
            self.assertTrue(
                ru._ASSUMES_WORKPLACE_RE.search(question)
                or ru._is_senior_question(question)
                or ru._ASSUMES_JOB_RE.search(question),
                f'not filtered for a fresher: {question}')

    def test_college_questions_are_not_filtered(self):
        for question in self.FRESHER_SAFE:
            self.assertFalse(ru._ASSUMES_WORKPLACE_RE.search(question),
                             f'wrongly filtered: {question}')
        # "team", "project" and "deadline" must stay usable — they are real
        # fresher experience, not workplace-only words.
        self.assertFalse(ru._ASSUMES_WORKPLACE_RE.search('your project team missed a deadline'))

    def test_hiring_decisions_are_senior_only(self):
        for question in ('How do you evaluate cultural fit versus skill fit?',
                         'How do you shortlist candidates for a role?'):
            self.assertTrue(ru._is_senior_question(question), question)

    def test_regexes_compiled_intact(self):
        """A literal backspace instead of \b silently matches nothing."""
        for name in ('_ASSUMES_WORKPLACE_RE', '_ASSUMES_JOB_RE', '_SENIOR_ONLY_RE', '_FRESHER_SAFE_RE'):
            pattern = getattr(ru, name).pattern
            self.assertNotIn('\x08', pattern, f'{name} has a backspace where \b was meant')

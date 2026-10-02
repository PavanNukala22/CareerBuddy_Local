"""Tests for employer candidate-search skill matching.

Run with:  python manage.py test jobs_app
"""
from django.test import SimpleTestCase, TestCase

# Absolute import: jobs_app has no __init__.py, so unittest's loader cannot
# resolve a relative import from this module.
from jobs_app.views import skill_term_hits


class SkillTermMatchingTests(SimpleTestCase):
    """Regression: the search fell back to a plain substring test, so "java"
    matched every candidate whose resume said "JavaScript"."""

    def test_java_does_not_match_javascript(self):
        self.assertEqual(skill_term_hits('java', 'Git HTML/CSS JavaScript'), 0)

    def test_java_matches_java(self):
        self.assertEqual(skill_term_hits('java', 'Skills: Java, Spring Boot'), 1)

    def test_counts_only_genuine_occurrences(self):
        self.assertEqual(skill_term_hits('java', 'Core Java and JavaScript'), 1)

    def test_javascript_still_matches_itself(self):
        self.assertEqual(skill_term_hits('javascript', 'Skills: JavaScript, React'), 1)

    def test_sql_does_not_match_mysql(self):
        self.assertEqual(skill_term_hits('sql', 'MySQL and PostgreSQL work'), 0)

    def test_react_does_not_match_reactjs(self):
        self.assertEqual(skill_term_hits('react', 'reactjs developer'), 0)

    def test_go_does_not_match_golang(self):
        self.assertEqual(skill_term_hits('go', 'Golang, going forward'), 0)

    def test_punctuated_skills_match(self):
        """\\b is unusable for these, hence the custom lookarounds."""
        self.assertEqual(skill_term_hits('c++', 'Languages: C++, Python'), 1)
        self.assertEqual(skill_term_hits('c#', 'Stack: C# and .NET'), 1)
        self.assertEqual(skill_term_hits('.net', 'Stack: C# and .NET'), 1)

    def test_single_letter_c_does_not_match_cplusplus(self):
        self.assertEqual(skill_term_hits('c', 'Languages: C++, Python'), 0)

    def test_matching_is_case_insensitive(self):
        self.assertEqual(skill_term_hits('JAVA', 'core java developer'), 1)

    def test_empty_inputs_are_safe(self):
        self.assertEqual(skill_term_hits('', 'anything'), 0)
        self.assertEqual(skill_term_hits('java', ''), 0)
        self.assertEqual(skill_term_hits(None, None), 0)


class ItCustomSkillsTests(TestCase):
    """IT postings: employers can type skills; those skills persist."""

    BASE = {
        'job_category': 'it', 'title': 'Backend Developer', 'description': 'Build APIs.',
        'job_type': 'full_time', 'experience': '1-2', 'salary_min': '30000',
        'salary_max': '50000', 'salary_format': 'monthly', 'location': 'Chennai',
        'openings': '2', 'status': 'active', 'work_environment': 'wfo',
        'notice_period': 'immediate', 'gender_preference': 'both',
        'interview_mode': 'virtual', 'education': 'ug',
    }

    def setUp(self):
        from django.contrib.auth import get_user_model
        from jobs_app.models import EmployerProfile

        user = get_user_model().objects.create_user(username='acme_hr', password='x')
        self.employer = EmployerProfile.objects.create(user=user, company_name='Acme')

    def _form(self, skills, mandatory, **extra):
        from django.http import QueryDict
        from jobs_app.forms import JobPostingForm

        data = QueryDict(mutable=True)
        data.update({**self.BASE, **extra})
        data.setlist('skills', skills)
        data['mandatory_skills'] = ','.join(mandatory)
        return JobPostingForm(data, employer=self.employer)

    def test_typed_skills_are_saved_with_preset_ones(self):
        form = self._form(['Python', 'Django', 'Communication', 'AWS'], ['Python', 'Django', 'AWS'])
        self.assertTrue(form.is_valid(), form.errors)
        job = form.save(commit=False)
        job.employer = self.employer
        job.save()
        self.assertEqual(job.get_mandatory_skills_list(), ['Python', 'Django', 'AWS'])
        self.assertIn('Communication', job.get_skills_list())

    def test_typed_skills_from_earlier_postings_are_offered_again(self):
        first = self._form(['Python', 'Django', 'Kubernetes'], ['Python', 'Django', 'Kubernetes'])
        self.assertTrue(first.is_valid(), first.errors)
        job = first.save(commit=False)
        job.employer = self.employer
        job.save()

        from jobs_app.forms import JobPostingForm
        fresh = JobPostingForm(employer=self.employer)
        for skill in ('Python', 'Django', 'Kubernetes'):
            self.assertIn(skill, fresh.it_skill_options)
        # ...but never to another employer.
        self.assertNotIn('Kubernetes', JobPostingForm().it_skill_options)

    def test_invalid_typed_skill_is_rejected(self):
        for bad in ('Python, Django', '!!!', 'x' * 41, '1234'):
            form = self._form([bad, 'Teamwork', 'Leadership', 'Communication'],
                              ['Teamwork', 'Leadership', 'Communication'])
            self.assertFalse(form.is_valid(), bad)
            self.assertIn('skills', form.errors, bad)

    def test_typed_skills_only_for_it(self):
        form = self._form(['Python', 'Civil Engineering', 'Instrumentation', 'Electronics'],
                          ['Civil Engineering', 'Instrumentation', 'Electronics'],
                          job_category='non_it', job_classification='technical', department='engineering')
        self.assertFalse(form.is_valid())
        self.assertIn('skills', form.errors)

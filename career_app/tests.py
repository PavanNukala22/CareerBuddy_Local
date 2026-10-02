from django.test import TestCase

# Create your tests here.


class ExpiredJobRecommendationTests(TestCase):
    """A posting past its deadline is no longer recommended."""

    def test_past_deadline_jobs_are_not_recommended(self):
        from datetime import timedelta

        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from career_app.views import _get_matched_jobs
        from jobs_app.models import EmployerProfile, JobPosting

        user = get_user_model().objects.create_user(username='deadline_hr', password='x')
        employer = EmployerProfile.objects.create(user=user, company_name='Acme')
        today = timezone.localdate()

        def job(title, deadline):
            return JobPosting.objects.create(
                employer=employer, title=title, description='d', job_type='full_time',
                experience='fresher', location='Chennai', skills_required='Python',
                status='active', deadline=deadline)

        expired = job('Expired', today - timedelta(days=1))
        due_today = job('Due today', today)
        future = job('Future', today + timedelta(days=7))
        no_deadline = job('No deadline', None)

        recommended = _get_matched_jobs(['Python'], years_experience=0, max_results=None)
        self.assertNotIn(expired, recommended)
        for open_job in (due_today, future, no_deadline):
            self.assertIn(open_job, recommended)

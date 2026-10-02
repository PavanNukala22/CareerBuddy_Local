from django.urls import path, include
from jobs_app import views as job_views

app_name = 'employer_portal'

urlpatterns = [
    # Public job-seeker facing home (also named job_home globally)
    path('', job_views.home, name='home'),
    path('jobs/<int:pk>/', job_views.job_detail, name='job_detail'),
    path('candidates/download-csv/', job_views.download_candidates_csv, name='download_candidates_csv'),

    # Auth (employer login/register)
    path('accounts/', include('accounts_app.urls')),

    # Employer dashboard & management
    path('employer/', include('jobs_app.employer_urls')),
]

from django.urls import path
from . import views



urlpatterns = [
    path('dashboard/', views.employer_dashboard, name='dashboard'),
    path('profile/create/', views.employer_profile_create, name='employer_profile_create'),
    path('profile/edit/', views.employer_profile_edit, name='employer_profile_edit'),
    path('jobs/new/', views.job_create, name='job_create'),
    path('jobs/<int:pk>/edit/', views.job_edit, name='job_edit'),
    path('jobs/<int:pk>/delete/', views.job_delete, name='job_delete'),
    path('jobs/<int:pk>/applications/', views.job_applications, name='job_applications'),
    path('jobs/<int:pk>/', views.job_detail, name='job_detail'),
    path('applications/', views.all_applications, name='all_applications'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('job-openings/', views.job_openings, name='job_openings'),
    path('resume-apply/', views.resume_apply_job, name='resume_apply_job'),
    path('candidates/search/', views.search_candidates, name='search_candidates'),
    path('candidates/download-csv/', views.download_candidates_csv, name='download_candidates_csv'),
]

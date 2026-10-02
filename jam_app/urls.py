from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'jam'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('session/start/', views.jam_session, name='jam_session'),
    path('session/start/<int:topic_id>/', views.jam_session_with_topic, name='jam_session_topic'),
    path('session/save-audio/', views.save_audio, name='save_audio'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('history/', views.history, name='history'),
    path('topics/', views.topics_list, name='topics'),
    path('profile/', views.profile_view, name='profile'),
    
    # Assessment Module
    path('assessment/start/', views.start_assessment, name='start_assessment'),
    path('assessment/session/<int:session_id>/', views.assessment_session, name='assessment_session'),
    path('assessment/result/<int:assessment_id>/', views.assessment_result, name='assessment_result'),
    
    # Deletion / Reset
    path('session/delete/<int:session_id>/', views.delete_session, name='delete_session'),
    path('reset-progress/', views.reset_progress, name='reset_progress'),
    
    # Seamless Assessment Flow
    path('assessment/delete/<int:assessment_id>/', views.delete_assessment, name='delete_assessment'),

    # Direct Completion Flow
    path('session/complete/<int:session_id>/', views.complete_session, name='complete_session'),
]

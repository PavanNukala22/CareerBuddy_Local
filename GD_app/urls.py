from django.urls import path
from . import views

app_name = 'GD_app'

urlpatterns = [
    path('', views.home, name='home'),
    path('create/', views.create_session, name='create_session'),
    path('room/<int:session_id>/', views.gd_room, name='gd_room'),
    path('report/<int:session_id>/', views.session_report, name='session_report'),
    path('api/sessions/', views.api_sessions, name='api_sessions'),
]

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('register/', views.register, name='job_register'),
    path('login/', views.EmployerLoginView.as_view(template_name='accounts/login.html'), name='job_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='job_logout'),
    
    # Employer specific auth
    path('employer/login/', views.EmployerLoginView.as_view(), name='employer_login'),
    path('employer/register/', views.employer_register, name='employer_register'),
]

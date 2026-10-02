from django.urls import path
from . import views

urlpatterns = [
    path('', views.activity_list, name='activity_list'),
    path('workshop/', views.workshop_dashboard, name='workshop_dashboard'),
    path('module/<slug:module>/', views.activity_module_redirect, name='activity_module_redirect'),
    path('<int:pk>/', views.activity_detail, name='activity_detail'),
    path('<int:activity_pk>/sub/<int:sub_pk>/', views.sub_activity_detail, name='sub_activity_detail'),
    path('exercise/<int:exercise_pk>/', views.exercise_detail, name='exercise_detail'),
    path('exercise/<int:exercise_pk>/submit/', views.submit_exercise, name='submit_exercise'),
    path('exercise/attempt/<int:attempt_pk>/delete/', views.delete_attempt, name='delete_attempt'),
    path('sub/<int:sub_pk>/complete/', views.mark_sub_complete, name='mark_sub_complete'),

    # AI Module analyze endpoints
    path('exercise/<int:exercise_pk>/analyze/speaking/', views.analyze_speaking, name='analyze_speaking'),
    path('exercise/<int:exercise_pk>/analyze/writing/', views.analyze_writing, name='analyze_writing'),
    path('exercise/<int:exercise_pk>/analyze/listening/', views.analyze_listening, name='analyze_listening'),
    path('exercise/<int:exercise_pk>/analyze/reading/', views.analyze_reading, name='analyze_reading'),

    # OOP Mastery quiz — server-side question bank (random 50 of 300)
    path('oop-quiz/questions/', views.oop_quiz_questions, name='oop_quiz_questions'),
    path('oop-quiz/submit/', views.oop_quiz_submit, name='oop_quiz_submit'),

    # Generic subject quiz (python, dsa, …) — same protection model
    path('quiz/<slug:subject>/questions/', views.quiz_questions, name='quiz_questions'),
    path('quiz/<slug:subject>/submit/', views.quiz_submit, name='quiz_submit'),

    # AMCAT full mock — 5 modules, random questions per module (answers server-side)
    path('amcat/questions/', views.amcat_questions, name='amcat_questions'),
    path('amcat/submit/', views.amcat_submit, name='amcat_submit'),

    # CoCubes full mock — 4 sections (3 MCQ graded + Programming free-text)
    path('cocubes/questions/', views.cocubes_questions, name='cocubes_questions'),
    path('cocubes/submit/', views.cocubes_submit, name='cocubes_submit'),
]

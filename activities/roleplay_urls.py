from django.urls import path
from activities import views as roleplay_views

urlpatterns = [
    path('', roleplay_views.roleplay_home, name='roleplay_home'),
    path('practice/', roleplay_views.roleplay_practice, name='roleplay_practice'),
    path('analyze/', roleplay_views.analyze_roleplay, name='analyze_roleplay'),
    path('<str:feature>/', roleplay_views.roleplay_practice_view, name='roleplay_practice_view'),
]

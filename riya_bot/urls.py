from django.urls import path
from . import views

urlpatterns = [
    path('api/riya/chat/', views.riya_chat, name='riya_chat'),
    path('api/riya/chat/stream/', views.riya_chat_stream, name='riya_chat_stream'),
    path('api/voice/transcribe/', views.riya_voice_transcribe, name='riya_voice_transcribe'),
    path('api/voice/tts/', views.riya_tts, name='riya_tts'),
    path('api/voice/tts/stream/', views.riya_tts_stream, name='riya_tts_stream'),
    
    # Optional aliases
    path('api/aria/chat/', views.riya_chat, name='aria_chat'),
    path('api/aria/voice/transcribe/', views.riya_voice_transcribe, name='aria_voice_transcribe'),
    path('api/aria/voice/tts/', views.riya_tts, name='aria_tts'),
]

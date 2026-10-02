"""
ASGI configuration for business_english_lms project.
Supports HTTP (Django) and WebSocket (Django Channels) connections.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'business_english_lms.settings')

django_asgi_app = get_asgi_application()

# Import WebSocket URL patterns
from GD_app.routing import websocket_urlpatterns as gd_ws_patterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            gd_ws_patterns
        )
    ),
})

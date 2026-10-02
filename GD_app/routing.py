from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/GD_app/(?P<session_id>\d+)/$', consumers.GDConsumer.as_asgi()),
]

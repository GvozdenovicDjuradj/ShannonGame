from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<board_number>\w+)/$', consumers.GameConsumer.as_asgi()),
]
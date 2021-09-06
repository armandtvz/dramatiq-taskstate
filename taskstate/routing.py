"""
URL routing for django-channels consumers.
Path's must be prefixed with `ws/`.
"""

from django.urls import re_path

from . import consumers


websocket_urlpatterns = [
    re_path(r'^ws/get-task-status/$', consumers.CheckTaskStatus.as_asgi()),
    re_path(r'^ws/set-task-seen/$', consumers.SetTaskSeen.as_asgi()),
]

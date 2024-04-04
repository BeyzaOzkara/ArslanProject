from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from .consumers import NotificationConsumer

# application = ProtocolTypeRouter({
#     'websocket': AuthMiddlewareStack(
#         URLRouter([
#             re_path('ws/notifications/', NotificationConsumer.as_asgi()),
#         ])
#     ),
# })

websocket_urlpatterns = [
    re_path(r"ws/notifications/", NotificationConsumer.as_asgi()),
]
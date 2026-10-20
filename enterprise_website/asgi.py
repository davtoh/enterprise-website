"""
ASGI config for enterprise_website project.

It exposes the ASGI callable as a module-level variable named ``application``.

For Channels 4.x + Django 5.x:
ProtocolTypeRouter routes 'http' requests through Django's ASGI application
and 'websocket' requests through Channels routing.
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enterprise_website.settings")

# Initialize Django ASGI application early to ensure the AppRegistry is populated
# before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(...))),
})

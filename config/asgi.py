import os
from django.conf import settings
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator

# Set the settings module for your project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure the App Registry is populated
django_asgi_app = get_asgi_application()

# Import routing and custom middleware after get_asgi_application()
from chat.routing import websocket_urlpatterns
from chat.middleware import JWTAuthMiddleware, UUIDAuthMiddlewareStack


def _build_websocket_origin_validator(application):
    if settings.DEBUG:
        trusted_origins = list(dict.fromkeys([
            *getattr(settings, 'CORS_ALLOWED_ORIGINS', []),
            *getattr(settings, 'CSRF_TRUSTED_ORIGINS', []),
            'http://localhost:3000',
            'http://127.0.0.1:3000',
        ]))
        return OriginValidator(application, trusted_origins)

    return AllowedHostsOriginValidator(application)

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": _build_websocket_origin_validator(
        # UUIDAuthMiddlewareStack (Session logic) must wrap JWTAuthMiddleware
        # so that 'scope["user"]' is populated before JWT attempts an override.
        UUIDAuthMiddlewareStack(
            JWTAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            )
        )
    ),
})
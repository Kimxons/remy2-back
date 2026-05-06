import logging
from typing import Optional

from urllib.parse import parse_qs

from channels.sessions import SessionMiddlewareStack
from channels.auth import AuthMiddleware
from channels.db import database_sync_to_async

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core.exceptions import ObjectDoesNotExist

from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)
User = get_user_model()


# =========================
# SESSION AUTH (UNCHANGED LOGIC, SAFER)
# =========================
@database_sync_to_async
def get_user_for_scope(scope: dict) -> User:
    """
    Load authenticated user from Django session.
    """

    session = scope.get('session')

    if not session:
        logger.debug("No session found in scope")
        return AnonymousUser()

    session_key = getattr(session, "session_key", None)

    if not session_key:
        logger.debug("Session exists but has no session_key")
        return AnonymousUser()

    try:
        session_db = Session.objects.get(session_key=session_key)
        session_data = session_db.get_decoded()

        user_id = session_data.get('_auth_user_id')

        if not user_id:
            logger.debug(f"No user ID in session {session_key[:8]}...")
            return AnonymousUser()

        user = User.objects.get(pk=user_id)

        logger.debug(f"Successfully loaded user {user.username} from session")

        return user

    except Session.DoesNotExist:
        logger.warning(f"Session {session_key[:8]}... not found")
        return AnonymousUser()

    except ObjectDoesNotExist:
        logger.warning(f"User {user_id} not found")
        return AnonymousUser()

    except Exception as e:
        logger.error(
            f"Unexpected session error: {type(e).__name__}: {e}",
            exc_info=True
        )
        return AnonymousUser()


# =========================
# UUID SESSION MIDDLEWARE (UNCHANGED)
# =========================
class UUIDAuthMiddleware(AuthMiddleware):
    async def resolve_scope(self, scope: dict):
        scope['user'] = await get_user_for_scope(scope)

        user = scope['user']
        path = scope.get('path', 'unknown')

        session = scope.get('session')
        session_key = getattr(session, "session_key", None)

        if user and user.is_authenticated:
            logger.info(
                f"WebSocket auth: User {user.username} connecting to {path}"
            )
        else:
            logger.info(
                f"WebSocket auth: Guest user (session={session_key[:8] if session_key else 'None'}) "
                f"connecting to {path}"
            )


def UUIDAuthMiddlewareStack(inner):
    return SessionMiddlewareStack(UUIDAuthMiddleware(inner))


# =========================
# JWT AUTH (FIXED BUT SAME STYLE)
# =========================
@database_sync_to_async
def get_user_from_token(token):
    try:
        if not token:
            return AnonymousUser()

        access_token = AccessToken(token)
        user_id = access_token.get("user_id")

        if not user_id:
            return AnonymousUser()

        return User.objects.get(pk=user_id)

    except Exception as e:
        logger.warning(f"JWT auth failed: {e}")
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    FIX: Does NOT replace session system blindly.
    Only overrides user if JWT is valid.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token = params.get("token", [None])[0]

        # 1. Start with session user (already set)
        user = scope.get("user", AnonymousUser())

        # 2. If JWT exists, try override
        if token:
            jwt_user = await get_user_from_token(token)

            if jwt_user and not isinstance(jwt_user, AnonymousUser):
                user = jwt_user

        scope["user"] = user

        return await self.app(scope, receive, send)
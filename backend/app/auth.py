"""
Single shared-secret auth.

There's no multi-user login here on purpose (see the README's stack
notes) — but an unauthenticated local API is still one stray port-forward
or one bad Docker network config away from being reachable by something
other than you. This dependency requires the token from .env on every
request; it's a tripwire, not a full auth system.
"""
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    if credentials is None or not hmac.compare_digest(credentials.credentials, settings.api_auth_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing bearer token")

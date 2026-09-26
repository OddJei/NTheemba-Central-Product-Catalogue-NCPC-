import hashlib
import hmac
import threading
import time
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_session
from .enums import PrincipalRole
from .errors import AuthenticationError, AuthorizationError, RateLimitError
from .models import ApiClient

# Scopes are constrained by the authenticated role. A mistakenly over-scoped
# business credential must never become an administrator credential.
ROLE_ALLOWED_SCOPES: dict[PrincipalRole, frozenset[str]] = {
    PrincipalRole.BUSINESS: frozenset({"catalogue:read", "submissions:read", "submissions:write", "coverage:read", "coverage:write"}),
    PrincipalRole.NTHEEMBA: frozenset({"catalogue:read", "coverage:read", "discovery:read"}),
    PrincipalRole.REVIEWER: frozenset({"catalogue:read", "reviews:read", "reviews:decide", "identities:merge", "publications:read"}),
    PrincipalRole.ADMIN: frozenset({"*"}),
}


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Principal:
    client_id: str
    role: PrincipalRole
    business_id: str | None
    scopes: frozenset[str]

    def require_scope(self, scope: str) -> None:
        allowed = ROLE_ALLOWED_SCOPES[self.role]
        if "*" not in allowed and scope not in allowed:
            raise AuthorizationError("principal role is not permitted for this operation")
        if "*" not in self.scopes and scope not in self.scopes:
            raise AuthorizationError("required scope is not granted")

    def require_business(self, business_id: str) -> None:
        if self.role == PrincipalRole.BUSINESS and self.business_id != business_id:
            raise AuthorizationError("business scope mismatch")


class FixedWindowRateLimiter:
    """Per-process safety limit; deployment edge limits remain the outer control."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._windows: dict[str, tuple[int, int]] = {}

    def check(self, key: str, limit: int) -> None:
        minute = int(time.time() // 60)
        with self._lock:
            stored_minute, count = self._windows.get(key, (minute, 0))
            if stored_minute != minute:
                stored_minute, count = minute, 0
            if count >= limit:
                raise RateLimitError("request rate limit exceeded")
            self._windows[key] = (stored_minute, count + 1)


rate_limiter = FixedWindowRateLimiter()


def authenticate_token(session: Session, token: str) -> Principal:
    digest = token_digest(token)
    candidates = session.scalars(select(ApiClient).where(ApiClient.active.is_(True))).all()
    client = next(
        (candidate for candidate in candidates if hmac.compare_digest(candidate.token_digest, digest)),
        None,
    )
    if client is None:
        raise AuthenticationError("invalid credentials")
    rate_limiter.check(client.client_id, get_settings().rate_limit_per_minute)
    return Principal(
        client_id=client.client_id,
        role=client.role,
        business_id=client.business_id,
        scopes=frozenset(client.scopes),
    )


def get_principal(
    authorization: str | None = Header(default=None),
    session: Session = Depends(get_session),
) -> Principal:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.casefold() != "bearer" or not token:
        raise AuthenticationError("bearer authentication required")
    return authenticate_token(session, token)

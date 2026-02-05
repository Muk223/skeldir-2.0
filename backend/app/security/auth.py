from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

from fastapi import Header, Request
import jwt
from jwt import InvalidTokenError, PyJWKClient

from app.core.config import settings
from app.core.identity import resolve_user_id
from app.observability.context import set_tenant_id, set_user_id


class AuthError(Exception):
    def __init__(self, *, status_code: int, title: str, detail: str, type_url: str) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type_url = type_url
        super().__init__(detail)


@dataclass(frozen=True)
class AuthContext:
    tenant_id: UUID
    user_id: UUID
    subject: Optional[str]
    issuer: Optional[str]
    audience: Optional[str | list[str]]
    claims: dict[str, Any]


def _get_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise AuthError(
            status_code=401,
            title="Authentication Failed",
            detail="Missing Authorization header.",
            type_url="https://api.skeldir.com/problems/authentication-failed",
        )
    stripped = authorization.strip()
    if not stripped.lower().startswith("bearer "):
        raise AuthError(
            status_code=401,
            title="Authentication Failed",
            detail="Authorization header must be a Bearer token.",
            type_url="https://api.skeldir.com/problems/authentication-failed",
        )
    return stripped.split(" ", 1)[1].strip()


def _ensure_auth_configured() -> None:
    if settings.AUTH_JWT_SECRET or settings.AUTH_JWT_JWKS_URL:
        if not settings.AUTH_JWT_ALGORITHM:
            raise AuthError(
                status_code=500,
                title="Internal Server Error",
                detail="JWT algorithm is not configured.",
                type_url="https://api.skeldir.com/problems/internal-server-error",
            )
        return
    raise AuthError(
        status_code=500,
        title="Internal Server Error",
        detail="JWT validation is not configured.",
        type_url="https://api.skeldir.com/problems/internal-server-error",
    )


def _decode_token(token: str) -> dict[str, Any]:
    _ensure_auth_configured()
    options = {"require": ["exp"]}
    decode_kwargs: dict[str, Any] = {"options": options}
    if settings.AUTH_JWT_ISSUER:
        decode_kwargs["issuer"] = settings.AUTH_JWT_ISSUER
    if settings.AUTH_JWT_AUDIENCE:
        decode_kwargs["audience"] = settings.AUTH_JWT_AUDIENCE

    if settings.AUTH_JWT_JWKS_URL:
        jwks_client = PyJWKClient(settings.AUTH_JWT_JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=[settings.AUTH_JWT_ALGORITHM],
            **decode_kwargs,
        )
    return jwt.decode(
        token,
        settings.AUTH_JWT_SECRET,
        algorithms=[settings.AUTH_JWT_ALGORITHM],
        **decode_kwargs,
    )


def _require_tenant_id(claims: dict[str, Any]) -> UUID:
    tenant_id = claims.get("tenant_id")
    if not tenant_id:
        raise AuthError(
            status_code=401,
            title="Authentication Failed",
            detail="Missing tenant_id claim.",
            type_url="https://api.skeldir.com/problems/authentication-failed",
        )
    try:
        return UUID(str(tenant_id))
    except ValueError as exc:
        raise AuthError(
            status_code=401,
            title="Authentication Failed",
            detail="Invalid tenant_id claim.",
            type_url="https://api.skeldir.com/problems/authentication-failed",
        ) from exc


def _resolve_user_id(claims: dict[str, Any]) -> UUID:
    candidate = claims.get("user_id") or claims.get("sub")
    return resolve_user_id(candidate)


def get_auth_context(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthContext:
    token = _get_bearer_token(authorization)
    try:
        claims = _decode_token(token)
    except InvalidTokenError as exc:
        raise AuthError(
            status_code=401,
            title="Authentication Failed",
            detail="Invalid or expired JWT token.",
            type_url="https://api.skeldir.com/problems/authentication-failed",
        ) from exc

    tenant_id = _require_tenant_id(claims)
    user_id = _resolve_user_id(claims)
    auth_context = AuthContext(
        tenant_id=tenant_id,
        user_id=user_id,
        subject=claims.get("sub"),
        issuer=claims.get("iss"),
        audience=claims.get("aud"),
        claims=claims,
    )
    request.state.auth_context = auth_context
    set_tenant_id(tenant_id)
    set_user_id(user_id)
    return auth_context

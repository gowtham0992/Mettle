from __future__ import annotations

from contextvars import ContextVar, Token


_principal: ContextVar[str | None] = ContextVar("mettle_principal", default=None)


class AuthenticationRequired(PermissionError):
    """Raised when a live AWS operation has no verified caller identity."""


def set_principal(subject: str | None) -> Token[str | None]:
    return _principal.set(subject)


def reset_principal(token: Token[str | None]) -> None:
    _principal.reset(token)


def require_principal() -> str:
    subject = _principal.get()
    if not subject:
        raise AuthenticationRequired("Sign in to run the live AgentCore workflow.")
    return subject

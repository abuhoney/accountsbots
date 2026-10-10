"""Domain errors + centralized error handler (Section 25).

Categories: user_input / network / rate_limit / permission / internal.
Users only ever see a friendly message with an error reference."""
from __future__ import annotations

import asyncio
import os
import uuid


class BotError(Exception):
    """Base class for all domain errors raised inside flows."""

    kind = "internal"


class UserInputError(BotError):
    """The user sent something we cannot accept (bad format, wrong type)."""

    kind = "user_input"


class NetworkError(BotError):
    """A network call failed; retrying later may succeed."""

    kind = "network"


class RateLimitError(BotError):
    """Too many requests; the user must wait retry_after seconds."""

    kind = "rate_limit"

    def __init__(self, message: str = "Too many requests.", retry_after: int = 10) -> None:
        super().__init__(message)
        self.retry_after = int(retry_after)


class AccessDeniedError(BotError):
    """The user is not allowed to perform this action (permission category)."""

    kind = "permission"


class InternalError(BotError):
    """An internal bug or unexpected condition."""

    kind = "internal"


FRIENDLY_MESSAGES = {
    "user_input": "That input does not look right. Please try again.",
    "network": "Network problem on our side. Please try again in a moment.",
    "rate_limit": "Too many requests. Please wait {retry_after}s and try again.",
    "permission": "You are not allowed to do this.",
    "internal": "Something went wrong (ref {error_id}). The team has been notified.",
}

ERROR_COUNTERS: dict[str, int] = {"total": 0, "user_input": 0, "network": 0, "rate_limit": 0,
    "permission": 0, "internal": 0}


def new_error_id() -> str:
    """Return a short, user-safe error reference like 'err#a3f9c1'."""
    return "err#" + uuid.uuid4().hex[:6]


def bump(kind: str) -> None:
    """Increment the in-memory error counters (exposed via /health)."""
    ERROR_COUNTERS["total"] = ERROR_COUNTERS.get("total", 0) + 1
    ERROR_COUNTERS[kind] = ERROR_COUNTERS.get(kind, 0) + 1


async def handle_exception(ctx, exc: BaseException, adapter, t_func=None) -> None:
    """Centralized error handling (Section 25).

    Logs the traceback, counts it, replies with a friendly message and
    reports internal errors to admins by DM. Never leaks a traceback.
    """
    from loguru import logger

    kind = getattr(exc, "kind", "internal")
    if isinstance(exc, asyncio.CancelledError):
        raise
    if isinstance(exc, BotError):
        logger.warning("flow error [{}]: {}", kind, exc)
    else:
        logger.exception("unhandled exception [{}]", type(exc).__name__)
        kind = "internal"
    bump(kind)
    error_id = new_error_id()
    lang = getattr(ctx, "language", "en") or "en"
    message = FRIENDLY_MESSAGES.get(kind, FRIENDLY_MESSAGES["internal"]).format(
        error_id=error_id, retry_after=getattr(exc, "retry_after", 10)
    )
    if t_func is not None:
        try:
            key = "error." + kind
            localized = t_func(lang, key, error_id=error_id,
                               retry_after=getattr(exc, "retry_after", 10))
            if localized and localized != key:
                message = localized
        except Exception:  # pragma: no cover - i18n must never break error handling
            logger.exception("i18n failure while formatting error message")
    try:
        await adapter.send_text(ctx, message)
    except Exception:
        logger.exception("failed to send the error reply to the user")
    if kind == "internal" and True:
        await report_to_admins(ctx, exc, error_id, adapter)


async def report_to_admins(ctx, exc: BaseException, error_id: str, adapter) -> None:
    """DM a short report to every admin (never includes secrets)."""
    from loguru import logger

    from bot import config as cfg

    if os.environ.get("ERROR_REPORT_TO_ADMINS", "true").lower() not in ("1", "true", "yes", "on"):
        return
    text = (
        "⚠️ Internal error " + error_id + "\n"
        + type(exc).__name__ + ": " + str(exc)[:400] + "\n"
        + "user_id=" + str(getattr(ctx, "user_id", 0))
        + " chat_id=" + str(getattr(ctx, "chat_id", 0))
    )
    for admin_id in cfg.ADMINS:
        try:
            await adapter.send_to_chat(admin_id, text)
        except Exception:
            logger.exception("failed to DM admin {}", admin_id)

"""Exponential backoff for provider rate limits (HTTP 429 / ResourceExhausted)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

BACKOFF_SECONDS = (5.0, 10.0, 20.0)


def is_rate_limit_error(exc: BaseException) -> bool:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status == 429:
        return True
    message = str(exc).lower()
    return any(
        token in message
        for token in (
            "429",
            "resourceexhausted",
            "resource exhausted",
            "rate limit",
            "too many requests",
            "quota exceeded",
        )
    )


def invoke_with_backoff(call: Callable[[], T], *, max_attempts: int = 4) -> T:
    last_exc: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return call()
        except BaseException as exc:  # noqa: BLE001 — retry only rate-limit class errors
            last_exc = exc
            if not is_rate_limit_error(exc) or attempt >= max_attempts - 1:
                raise
            delay = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc

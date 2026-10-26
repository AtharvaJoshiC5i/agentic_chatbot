"""Client-side RPM limiters per LLM provider (process-local)."""

from __future__ import annotations

import threading
import time
from collections import deque

_lock = threading.Lock()
_windows: dict[str, deque[float]] = {}


def _window_for(provider: str, max_rpm: int) -> tuple[deque[float], int]:
    key = f"{provider}:{max_rpm}"
    with _lock:
        if key not in _windows:
            _windows[key] = deque()
        return _windows[key], max_rpm


def acquire_llm_slot(provider: str, max_rpm: int) -> None:
    """Block until a request slot is available (rolling 60s window)."""
    if max_rpm <= 0:
        return
    window, cap = _window_for(provider, max_rpm)
    while True:
        with _lock:
            now = time.monotonic()
            while window and now - window[0] >= 60.0:
                window.popleft()
            if len(window) < cap:
                window.append(now)
                return
            wait_seconds = 60.0 - (now - window[0]) + 0.05
        time.sleep(max(wait_seconds, 0.1))


def reset_rate_limiters() -> None:
    """Test helper."""
    with _lock:
        _windows.clear()

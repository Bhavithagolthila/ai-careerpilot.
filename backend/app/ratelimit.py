"""Tiny in-memory limiter for failed logins (no extra dependency).

Limits: settings.login_max_attempts failures per settings.login_window_seconds, per IP + email.
Limitation: state lives in one process. With several workers/servers use Redis instead.
"""
import time
from collections import defaultdict, deque

from app.config import settings


class FailureLimiter:
    def __init__(self):
        self._fails: dict[str, deque] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque:
        q = self._fails[key]
        while q and now - q[0] > settings.login_window_seconds:
            q.popleft()
        if not q:
            self._fails.pop(key, None)  # do not keep memory for idle keys
        return q

    def blocked_for(self, key: str) -> int:
        """Seconds until the next attempt is allowed (0 = allowed)."""
        now = time.monotonic()
        q = self._prune(key, now)
        if len(q) >= settings.login_max_attempts:
            return max(1, int(settings.login_window_seconds - (now - q[0])))
        return 0

    def record_failure(self, key: str) -> None:
        self._fails[key].append(time.monotonic())

    def reset(self, key: str | None = None) -> None:
        self._fails.pop(key, None) if key else self._fails.clear()


login_limiter = FailureLimiter()

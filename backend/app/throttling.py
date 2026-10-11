import time
from collections import deque

from fastapi import HTTPException, Request, status

# Attempts are counted in this process only, which is enough for a single API
# container; a multi-instance deployment would keep these counters in Redis.
ATTEMPT_LIMIT = 8
WINDOW_SECONDS = 15 * 60
# Keys embed the address that was typed in, so an attacker cycling through unknown
# emails would otherwise grow this dict without limit. Once the cap is reached the
# windows that have already elapsed are dropped.
MAX_TRACKED_KEYS = 20_000
_attempts: dict[str, deque[float]] = {}


def _trim(attempts: deque[float]) -> deque[float]:
    cutoff = time.monotonic() - WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def _forget_elapsed_windows() -> None:
    for key in [key for key, attempts in _attempts.items() if not _trim(attempts)]:
        del _attempts[key]


def guard(key: str) -> None:
    """Refuse the request once a key has burned through its attempts in the window."""
    attempts = _attempts.get(key)
    # Reading must not create an entry, or an unauthenticated flood of new keys
    # would be enough to grow the table.
    if attempts is not None and len(_trim(attempts)) >= ATTEMPT_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts, please wait a few minutes")


def record_attempt(key: str) -> None:
    if key not in _attempts:
        if len(_attempts) >= MAX_TRACKED_KEYS:
            _forget_elapsed_windows()
        _attempts[key] = deque()
    _trim(_attempts[key]).append(time.monotonic())


def reset(key: str) -> None:
    _attempts.pop(key, None)


def caller(request: Request) -> str:
    return request.client.host if request.client else "unknown"

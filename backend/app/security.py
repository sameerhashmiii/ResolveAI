import hashlib
import secrets
import time
from asyncio import Lock
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from itertools import islice
from math import ceil

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_password_hasher = PasswordHasher()
RATE_LIMIT_DETAIL = "Too many requests"


@dataclass
class _Window:
    expires_at: float
    count: int


class FixedWindowRateLimiter:
    """Bounded, process-local fixed-window limiter for a single application worker."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
        cleanup_batch: int = 100,
    ) -> None:
        if max_keys < 1 or cleanup_batch < 1:
            raise ValueError("Limiter bounds must be positive")
        self._clock = clock
        self._max_keys = max_keys
        self._cleanup_batch = cleanup_batch
        self._windows: OrderedDict[str, _Window] = OrderedDict()
        self._lock = Lock()

    async def check(self, key: str, *, limit: int, window_seconds: int) -> int | None:
        """Consume one request, returning retry seconds when the request is limited."""
        if limit < 1 or window_seconds < 1:
            raise ValueError("Rate limit and window must be positive")
        async with self._lock:
            now = self._clock()
            self._cleanup(now)
            window = self._windows.get(key)
            if window is None or now >= window.expires_at:
                if window is None and len(self._windows) >= self._max_keys:
                    self._windows.popitem(last=False)
                self._windows[key] = _Window(expires_at=now + window_seconds, count=1)
                self._windows.move_to_end(key)
                return None
            if window.count >= limit:
                return max(1, ceil(window.expires_at - now))
            window.count += 1
            return None

    def _cleanup(self, now: float) -> None:
        keys = list(islice(self._windows, self._cleanup_batch))
        for key in keys:
            if now >= self._windows[key].expires_at:
                del self._windows[key]

    @property
    def key_count(self) -> int:
        return len(self._windows)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

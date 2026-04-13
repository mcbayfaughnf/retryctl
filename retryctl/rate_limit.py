"""Per-command rate limiting using a sliding window counter."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


class RateLimitExceeded(Exception):
    """Raised when the allowed call rate has been exceeded."""

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        super().__init__(
            f"Rate limit of {limit} calls per {window}s exceeded"
        )


@dataclass
class SlidingWindowCounter:
    """Tracks call timestamps within a rolling time window."""

    limit: int
    window: float  # seconds
    _timestamps: Deque[float] = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be a positive integer")
        if self.window <= 0:
            raise ValueError("window must be a positive number of seconds")

    def _evict_old(self, now: float) -> None:
        cutoff = now - self.window
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def allow(self, now: float | None = None) -> bool:
        """Return True and record the call if within the limit, else False."""
        now = now if now is not None else time.monotonic()
        self._evict_old(now)
        if len(self._timestamps) >= self.limit:
            return False
        self._timestamps.append(now)
        return True

    def check(self, now: float | None = None) -> None:
        """Like *allow* but raises *RateLimitExceeded* on violation."""
        if not self.allow(now):
            raise RateLimitExceeded(self.limit, self.window)

    @property
    def current_count(self) -> int:
        """Number of calls recorded in the current window."""
        self._evict_old(time.monotonic())
        return len(self._timestamps)

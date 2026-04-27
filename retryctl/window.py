"""Sliding time-window execution limiter for retry attempts."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


class WindowExceeded(Exception):
    """Raised when the attempt limit within the time window is breached."""

    def __init__(self, count: int, limit: int, window: float) -> None:
        self.count = count
        self.limit = limit
        self.window = window
        super().__init__(
            f"attempt limit {limit} exceeded within {window}s window "
            f"(current count: {count})"
        )


@dataclass
class WindowPolicy:
    """Configuration for a sliding-window attempt limiter."""

    limit: int
    window: float  # seconds

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be a positive integer")
        if self.window <= 0:
            raise ValueError("window must be positive")


@dataclass
class WindowTracker:
    """Tracks attempt timestamps within a rolling time window."""

    policy: WindowPolicy
    _timestamps: Deque[float] = field(default_factory=deque, init=False)

    def _evict(self, now: float) -> None:
        cutoff = now - self.policy.window
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def check(self) -> None:
        """Record an attempt; raise WindowExceeded if limit is breached."""
        now = time.monotonic()
        self._evict(now)
        if len(self._timestamps) >= self.policy.limit:
            raise WindowExceeded(
                count=len(self._timestamps),
                limit=self.policy.limit,
                window=self.policy.window,
            )
        self._timestamps.append(now)

    @property
    def current_count(self) -> int:
        """Number of attempts recorded within the current window."""
        self._evict(time.monotonic())
        return len(self._timestamps)

    def reset(self) -> None:
        """Clear all recorded timestamps."""
        self._timestamps.clear()

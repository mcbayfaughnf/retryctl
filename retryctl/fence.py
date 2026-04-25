"""Execution fence: block retries until a minimum number of successes
or failures have been observed within a sliding window."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Tuple


class FenceBlocked(Exception):
    """Raised when the fence prevents execution."""

    def __init__(self, reason: str, successes: int, failures: int) -> None:
        super().__init__(
            f"Fence blocked ({reason}): successes={successes} failures={failures}"
        )
        self.reason = reason
        self.successes = successes
        self.failures = failures


@dataclass
class FencePolicy:
    """Policy governing when the fence opens or closes."""

    min_successes: int = 1
    max_failures: int = 3
    window: float = 60.0  # seconds

    def __post_init__(self) -> None:
        if self.min_successes < 1:
            raise ValueError("min_successes must be >= 1")
        if self.max_failures < 1:
            raise ValueError("max_failures must be >= 1")
        if self.window <= 0:
            raise ValueError("window must be > 0")


@dataclass
class FenceTracker:
    """Tracks success/failure events within a sliding time window."""

    policy: FencePolicy
    _events: Deque[Tuple[float, bool]] = field(default_factory=deque, init=False)

    def _evict(self) -> None:
        cutoff = time.monotonic() - self.policy.window
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def record_success(self) -> None:
        self._events.append((time.monotonic(), True))

    def record_failure(self) -> None:
        self._events.append((time.monotonic(), False))

    @property
    def successes(self) -> int:
        self._evict()
        return sum(1 for _, ok in self._events if ok)

    @property
    def failures(self) -> int:
        self._evict()
        return sum(1 for _, ok in self._events if not ok)

    def check(self) -> None:
        """Raise FenceBlocked if the fence should block execution."""
        self._evict()
        f = self.failures
        s = self.successes
        if f >= self.policy.max_failures and s < self.policy.min_successes:
            raise FenceBlocked("too many failures", successes=s, failures=f)

    def reset(self) -> None:
        self._events.clear()

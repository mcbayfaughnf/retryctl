"""retry_budget.py – tracks a shared pool of retry attempts across runs.

A RetryBudget caps the *total* number of retries that may be consumed
within a rolling time window.  This prevents a single misbehaving command
from exhausting cluster-wide or process-wide retry allowances.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


class BudgetExhausted(Exception):
    """Raised when the retry budget has been fully consumed."""

    def __init__(self, used: int, limit: int, window: float) -> None:
        self.used = used
        self.limit = limit
        self.window = window
        super().__init__(
            f"Retry budget exhausted: {used}/{limit} retries used "
            f"within the last {window}s window."
        )


@dataclass
class RetryBudget:
    """A sliding-window retry budget.

    Parameters
    ----------
    limit:
        Maximum number of retries allowed within *window* seconds.
    window:
        Length of the sliding time window in seconds.
    """

    limit: int
    window: float
    _timestamps: Deque[float] = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError(f"limit must be positive, got {self.limit}")
        if self.window <= 0:
            raise ValueError(f"window must be positive, got {self.window}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def consume(self) -> None:
        """Record one retry attempt, raising BudgetExhausted if over limit."""
        self._evict_old()
        if len(self._timestamps) >= self.limit:
            raise BudgetExhausted(
                used=len(self._timestamps),
                limit=self.limit,
                window=self.window,
            )
        self._timestamps.append(time.monotonic())

    def remaining(self) -> int:
        """Return the number of retries still available in the current window."""
        self._evict_old()
        return max(0, self.limit - len(self._timestamps))

    @property
    def used(self) -> int:
        """Number of retries consumed in the current window."""
        self._evict_old()
        return len(self._timestamps)

    def reset(self) -> None:
        """Clear all recorded timestamps (useful for testing)."""
        self._timestamps.clear()

    def time_until_next(self) -> float:
        """Return seconds until at least one retry slot becomes available.

        Returns 0.0 if a slot is already available.  Useful for callers
        that want to sleep or surface a wait time rather than immediately
        raising on a full budget.
        """
        self._evict_old()
        if len(self._timestamps) < self.limit:
            return 0.0
        # The oldest timestamp is the next one to expire out of the window.
        oldest = self._timestamps[0]
        wait = (oldest + self.window) - time.monotonic()
        return max(0.0, wait)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_old(self) -> None:
        cutoff = time.monotonic() - self.window
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

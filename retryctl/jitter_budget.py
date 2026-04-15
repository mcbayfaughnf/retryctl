"""Jitter budget tracker: limits total cumulative jitter added across attempts."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


class BudgetExhausted(Exception):
    """Raised when the cumulative jitter budget has been exceeded."""

    def __init__(self, used: float, limit: float) -> None:
        self.used = used
        self.limit = limit
        super().__init__(
            f"Jitter budget exhausted: used {used:.3f}s of {limit:.3f}s limit"
        )


@dataclass
class JitterBudget:
    """Tracks cumulative jitter consumed across retry attempts.

    Parameters
    ----------
    limit:
        Maximum total seconds of jitter allowed for the lifetime of a run.
    """

    limit: float
    _used: float = field(default=0.0, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError(f"limit must be positive, got {self.limit}")

    @property
    def used(self) -> float:
        """Total jitter consumed so far (seconds)."""
        return self._used

    @property
    def remaining(self) -> float:
        """Remaining jitter budget (seconds)."""
        return max(0.0, self.limit - self._used)

    def consume(self, amount: float) -> float:
        """Record *amount* seconds of jitter, capping at the remaining budget.

        Returns the actual amount consumed (may be less than *amount* if the
        budget is nearly exhausted).  Raises :class:`BudgetExhausted` when the
        budget was already at zero before this call.
        """
        if amount < 0:
            raise ValueError(f"amount must be non-negative, got {amount}")
        with self._lock:
            if self._used >= self.limit:
                raise BudgetExhausted(self._used, self.limit)
            available = self.limit - self._used
            actual = min(amount, available)
            self._used += actual
            return actual

    def reset(self) -> None:
        """Reset consumed jitter to zero (useful between independent runs)."""
        with self._lock:
            self._used = 0.0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"JitterBudget(limit={self.limit!r}, used={self._used!r}, "
            f"remaining={self.remaining!r})"
        )

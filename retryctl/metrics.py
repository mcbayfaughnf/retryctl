"""Lightweight in-process metrics counters for retryctl."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MetricsSnapshot:
    """Immutable snapshot of current counter values."""

    counters: Dict[str, int] = field(default_factory=dict)

    def get(self, name: str, default: int = 0) -> int:
        return self.counters.get(name, default)


class MetricsCollector:
    """Thread-unsafe, in-process counter store.

    Tracks per-command metrics such as attempts, successes, and failures.
    """

    _KNOWN = {
        "attempts",
        "successes",
        "failures",
        "retries",
        "timeouts",
        "circuit_opens",
    }

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {k: 0 for k in self._KNOWN}

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def increment(self, name: str, amount: int = 1) -> None:
        """Increment *name* by *amount*.  Unknown."""
        if amount < 0:
            raise ValueError(f"amount must be non-negative, got {amount}")
        self._counters[name] = self._counters.get(name, 0) + amount

    def reset(self, name: str | None = None) -> None:
        """Reset *name* to zero, or all counters when *name* is None."""
        if name is None:
            for key in list(self._counters):
                self._counters[key] = 0
        else:
            if name in self._counters:
                self._counters[name] = 0

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, name: str, default: int = 0) -> int:
        return self._counters.get(name, default)

    def snapshot(self) -> MetricsSnapshot:
        """Return an immutable copy of the current counters."""
        return MetricsSnapshot(counters=dict(self._counters))

    def __repr__(self) -> str:  # pragma: no cover
        return f"MetricsCollector({self._counters!r})"

"""Per-key attempt quota enforcement."""
from __future__ import annotations
from dataclasses import dataclass, field
from time import monotonic
from typing import Dict, Optional


class QuotaExceeded(Exception):
    def __init__(self, key: str, limit: int, window: float) -> None:
        self.key = key
        self.limit = limit
        self.window = window
        super().__init__(
            f"Quota exceeded for '{key}': limit={limit} within {window}s window"
        )


@dataclass
class QuotaCounter:
    key: str
    limit: int
    window: float
    _timestamps: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        if self.window <= 0:
            raise ValueError("window must be positive")

    def _evict(self) -> None:
        cutoff = monotonic() - self.window
        self._timestamps = [t for t in self._timestamps if t >= cutoff]

    def record(self) -> None:
        self._evict()
        if len(self._timestamps) >= self.limit:
            raise QuotaExceeded(self.key, self.limit, self.window)
        self._timestamps.append(monotonic())

    @property
    def current(self) -> int:
        self._evict()
        return len(self._timestamps)

    def reset(self) -> None:
        self._timestamps.clear()


class QuotaRegistry:
    def __init__(self) -> None:
        self._counters: Dict[str, QuotaCounter] = {}

    def get_or_create(self, key: str, limit: int, window: float) -> QuotaCounter:
        if key not in self._counters:
            self._counters[key] = QuotaCounter(key=key, limit=limit, window=window)
        return self._counters[key]

    def reset(self, key: Optional[str] = None) -> None:
        if key is None:
            for c in self._counters.values():
                c.reset()
        elif key in self._counters:
            self._counters[key].reset()

    def remove(self, key: str) -> None:
        self._counters.pop(key, None)

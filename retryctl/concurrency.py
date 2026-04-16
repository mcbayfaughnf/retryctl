"""Concurrency limiter — cap the number of simultaneous retry attempts."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


class ConcurrencyExceeded(Exception):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"Concurrency limit of {limit} already reached")


@dataclass
class ConcurrencySemaphore:
    limit: int
    _sem: threading.Semaphore = field(init=False, repr=False)
    _lock: threading.Lock = field(init=False, repr=False)
    _active: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("limit must be >= 1")
        self._sem = threading.Semaphore(self.limit)
        self._lock = threading.Lock()

    def acquire(self, block: bool = False) -> None:
        """Acquire a slot.  Raises ConcurrencyExceeded when no slot is free."""
        acquired = self._sem.acquire(blocking=block)
        if not acquired:
            raise ConcurrencyExceeded(self.limit)
        with self._lock:
            self._active += 1

    def release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
        self._sem.release()

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    @property
    def available(self) -> int:
        return max(0, self.limit - self.active)

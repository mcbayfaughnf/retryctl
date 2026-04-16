"""Middleware that enforces a concurrency limit on command execution."""
from __future__ import annotations

from typing import Callable

from retryctl.concurrency import ConcurrencySemaphore, ConcurrencyExceeded
from retryctl.runner import CommandResult


class ConcurrencyMiddleware:
    """Wrap a next-callable with a concurrency semaphore.

    If the limit is already reached the middleware raises ConcurrencyExceeded
    rather than blocking, so the retry loop can treat it as a transient error.
    """

    def __init__(self, limit: int) -> None:
        self._sem = ConcurrencySemaphore(limit=limit)

    def __call__(self, next_fn: Callable[[], CommandResult]) -> CommandResult:
        self._sem.acquire(block=False)  # raises ConcurrencyExceeded if full
        try:
            return next_fn()
        finally:
            self._sem.release()

    @property
    def active(self) -> int:
        return self._sem.active

    @property
    def available(self) -> int:
        return self._sem.available

    @property
    def limit(self) -> int:
        return self._sem.limit

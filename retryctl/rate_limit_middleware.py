"""Middleware that enforces a SlidingWindowCounter rate limit."""
from __future__ import annotations

from typing import Callable

from retryctl.rate_limit import RateLimitExceeded, SlidingWindowCounter
from retryctl.runner import CommandResult


class RateLimitMiddleware:
    """Wraps a next-handler and enforces a sliding-window rate limit.

    If the limit is exceeded the middleware raises *RateLimitExceeded*
    rather than delegating to the next handler, so the caller (typically
    the retry loop) can decide whether to back off or abort.
    """

    def __init__(
        self,
        limit: int,
        window: float,
        *,
        counter: SlidingWindowCounter | None = None,
    ) -> None:
        self._counter = counter or SlidingWindowCounter(limit=limit, window=window)

    # ------------------------------------------------------------------
    # Middleware protocol
    # ------------------------------------------------------------------

    def __call__(
        self,
        next_handler: Callable[..., CommandResult],
        *args: object,
        **kwargs: object,
    ) -> CommandResult:
        """Check the rate limit then delegate to *next_handler*."""
        self._counter.check()  # raises RateLimitExceeded if over limit
        return next_handler(*args, **kwargs)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all recorded timestamps (useful in tests)."""
        self._counter._timestamps.clear()

    @property
    def current_count(self) -> int:
        return self._counter.current_count

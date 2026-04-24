"""Middleware that enforces backpressure before each attempt.

If the BackpressureTracker reports that load is too high the middleware
raises BackpressureActive instead of delegating to the next handler,
allowing the retry loop to back off or abort.
"""
from __future__ import annotations

from typing import Callable

from retryctl.backpressure import BackpressurePolicy, BackpressureTracker
from retryctl.runner import CommandResult


class BackpressureMiddleware:
    """Checks backpressure before forwarding to the next middleware."""

    def __init__(
        self,
        tracker: BackpressureTracker | None = None,
        policy: BackpressurePolicy | None = None,
    ) -> None:
        if tracker is not None:
            self._tracker = tracker
        else:
            self._tracker = BackpressureTracker(policy=policy or BackpressurePolicy())

    def __call__(
        self,
        next_fn: Callable[[], CommandResult],
        load: float | None = None,
    ) -> CommandResult:
        """Record *load* (if provided) then check for backpressure.

        Parameters
        ----------
        next_fn:
            The next handler in the middleware chain.
        load:
            Optional load sample in [0.0, 1.0] to record before the check.
        """
        if load is not None:
            self._tracker.record(load)
        self._tracker.check()
        return next_fn()

    @property
    def tracker(self) -> BackpressureTracker:
        return self._tracker

    def reset(self) -> None:
        """Reset the underlying tracker."""
        self._tracker.reset()

"""Middleware that applies a grace period policy to command execution."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.grace import GracePolicy, GracePeriodActive, GraceTracker
from retryctl.runner import CommandResult


class GraceMiddleware:
    """Wraps a next callable and suppresses failures within the grace window.

    When a failure occurs inside the grace period and *suppress_on_failure* is
    True the middleware raises :class:`GracePeriodActive` instead of returning
    the failed result, allowing the caller to decide how to handle it.
    """

    def __init__(
        self,
        policy: GracePolicy,
        tracker: Optional[GraceTracker] = None,
    ) -> None:
        self._policy = policy
        self._tracker = tracker if tracker is not None else GraceTracker(policy)

    def __call__(
        self,
        next_fn: Callable[..., CommandResult],
        *args,
        **kwargs,
    ) -> CommandResult:
        result = next_fn(*args, **kwargs)
        self._tracker.check(result)
        return result

    @property
    def tracker(self) -> GraceTracker:
        return self._tracker

    def reset(self) -> None:
        """Restart the grace window from now."""
        self._tracker.reset()

    def in_grace_period(self) -> bool:
        return self._tracker.in_grace_period()

    def remaining(self) -> float:
        return self._tracker.remaining()

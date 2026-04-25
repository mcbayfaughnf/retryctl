"""Middleware that enforces a FenceTracker around each attempt."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.fence import FencePolicy, FenceTracker
from retryctl.runner import CommandResult


class FenceMiddleware:
    """Blocks execution when the fence policy is violated.

    On each call:
    1. ``tracker.check()`` is called — raises ``FenceBlocked`` if blocked.
    2. The next middleware / runner is invoked.
    3. Success (exit_code == 0) records a success; otherwise a failure.
    """

    def __init__(
        self,
        policy: Optional[FencePolicy] = None,
        tracker: Optional[FenceTracker] = None,
    ) -> None:
        if tracker is not None:
            self._tracker = tracker
        else:
            self._tracker = FenceTracker(policy=policy or FencePolicy())

    def __call__(
        self,
        next_fn: Callable[[], CommandResult],
        *,
        result: Optional[CommandResult] = None,
    ) -> CommandResult:
        self._tracker.check()
        outcome: CommandResult = next_fn()
        if outcome.exit_code == 0:
            self._tracker.record_success()
        else:
            self._tracker.record_failure()
        return outcome

    @property
    def tracker(self) -> FenceTracker:
        return self._tracker

    def reset(self) -> None:
        self._tracker.reset()

"""Middleware that enforces a cooldown period between retry attempts."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.cooldown import CooldownPolicy, CooldownTracker
from retryctl.runner import CommandResult


class CooldownMiddleware:
    """Wraps a next-callable and enforces a per-command cooldown."""

    def __init__(self, policy: CooldownPolicy) -> None:
        self._tracker = CooldownTracker(policy=policy)

    def __call__(
        self,
        command: list[str],
        next_fn: Callable[[list[str]], CommandResult],
    ) -> CommandResult:
        self._tracker.check()
        result = next_fn(command)
        self._tracker.record()
        return result

    def reset(self) -> None:
        """Clear cooldown state (useful between independent runs)."""
        self._tracker.reset()

    @property
    def tracker(self) -> CooldownTracker:
        return self._tracker

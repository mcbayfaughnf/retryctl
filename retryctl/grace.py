"""Grace period support: suppress failures for an initial window after startup."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from retryctl.runner import CommandResult


class GracePeriodActive(Exception):
    """Raised when a failure occurs inside the grace window."""

    def __init__(self, elapsed: float, window: float) -> None:
        self.elapsed = elapsed
        self.window = window
        super().__init__(
            f"grace period active: {elapsed:.2f}s elapsed of {window:.2f}s window"
        )


@dataclass
class GracePolicy:
    window: float  # seconds
    suppress_on_failure: bool = True

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError(f"window must be positive, got {self.window}")


@dataclass
class GraceTracker:
    policy: GracePolicy
    _start: float = field(default_factory=time.monotonic, init=False)

    def elapsed(self) -> float:
        return time.monotonic() - self._start

    def in_grace_period(self) -> bool:
        return self.elapsed() < self.policy.window

    def remaining(self) -> float:
        return max(0.0, self.policy.window - self.elapsed())

    def check(self, result: CommandResult) -> None:
        """Raise GracePeriodActive if the result is a failure inside the window."""
        if result.exit_code == 0:
            return
        elapsed = self.elapsed()
        if elapsed < self.policy.window and self.policy.suppress_on_failure:
            raise GracePeriodActive(elapsed, self.policy.window)

    def reset(self) -> None:
        self._start = time.monotonic()

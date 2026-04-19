"""Pre-attempt sleep middleware with configurable delay before each command execution."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from retryctl.runner import CommandResult


@dataclass
class PreSleepConfig:
    """Configuration for pre-attempt sleep behaviour."""
    delay: float  # seconds to sleep before each attempt
    skip_first: bool = True  # skip sleep on the very first attempt

    def __post_init__(self) -> None:
        if self.delay < 0:
            raise ValueError(f"delay must be >= 0, got {self.delay}")


class PreSleepMiddleware:
    """Middleware that sleeps for a fixed delay before delegating to next.

    Useful when a command must not be hammered immediately after a previous
    run, independently of the backoff strategy used between retries.
    """

    def __init__(
        self,
        config: PreSleepConfig,
        *,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._config = config
        self._sleep = sleep_fn
        self._attempt = 0

    def __call__(
        self,
        next_fn: Callable[[], CommandResult],
    ) -> CommandResult:
        should_skip = self._config.skip_first and self._attempt == 0
        self._attempt += 1
        if not should_skip and self._config.delay > 0:
            self._sleep(self._config.delay)
        return next_fn()

    def reset(self) -> None:
        """Reset attempt counter (e.g. between independent runs)."""
        self._attempt = 0

    @property
    def attempt(self) -> int:
        return self._attempt

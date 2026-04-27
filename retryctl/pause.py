"""Pause/resume control for retry execution.

Allows an external signal to temporarily halt retry attempts between
executions without cancelling the overall run.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


class PauseTimeout(Exception):
    """Raised when a pause wait exceeds the allowed maximum duration."""

    def __init__(self, waited: float, limit: float) -> None:
        self.waited = waited
        self.limit = limit
        super().__init__(
            f"Pause wait exceeded limit: waited {waited:.2f}s of {limit:.2f}s allowed"
        )


@dataclass
class PausePolicy:
    """Configuration for pause behaviour."""

    max_wait: float = 0.0  # 0 means unlimited
    poll_interval: float = 0.05

    def __post_init__(self) -> None:
        if self.max_wait < 0:
            raise ValueError("max_wait must be >= 0")
        if self.poll_interval <= 0:
            raise ValueError("poll_interval must be > 0")


class PauseController:
    """Thread-safe pause/resume controller."""

    def __init__(self, policy: PausePolicy | None = None) -> None:
        self._policy = policy or PausePolicy()
        self._event = threading.Event()
        self._event.set()  # not paused by default
        self._paused_at: float | None = None

    @property
    def is_paused(self) -> bool:
        return not self._event.is_set()

    def pause(self) -> None:
        """Signal that execution should pause."""
        if not self.is_paused:
            self._paused_at = time.monotonic()
            self._event.clear()

    def resume(self) -> None:
        """Signal that execution may continue."""
        self._paused_at = None
        self._event.set()

    def wait_if_paused(self) -> float:
        """Block until resumed; return total seconds waited.

        Raises PauseTimeout if max_wait is exceeded.
        """
        if not self.is_paused:
            return 0.0

        start = time.monotonic()
        policy = self._policy

        while self.is_paused:
            waited = time.monotonic() - start
            if policy.max_wait > 0 and waited >= policy.max_wait:
                raise PauseTimeout(waited=waited, limit=policy.max_wait)
            self._event.wait(timeout=policy.poll_interval)

        return time.monotonic() - start

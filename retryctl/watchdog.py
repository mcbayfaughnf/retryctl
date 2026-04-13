"""Watchdog: per-attempt and global wall-clock deadline enforcement."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


class DeadlineExceeded(Exception):
    """Raised when a watchdog deadline has been passed."""

    def __init__(self, scope: str, deadline: float, now: float) -> None:
        self.scope = scope
        self.deadline = deadline
        self.now = now
        elapsed = now - (deadline - (now - deadline))
        super().__init__(
            f"{scope} deadline exceeded: deadline={deadline:.3f} now={now:.3f}"
        )


@dataclass
class Watchdog:
    """Tracks a global deadline and optionally a per-attempt deadline.

    Parameters
    ----------
    global_timeout:
        Maximum total seconds allowed for the whole retry run.  ``None``
        means no global limit.
    attempt_timeout:
        Maximum seconds allowed for a single attempt.  ``None`` means no
        per-attempt limit.
    """

    global_timeout: Optional[float] = None
    attempt_timeout: Optional[float] = None
    _start: float = field(default_factory=time.monotonic, init=False, repr=False)
    _attempt_start: Optional[float] = field(default=None, init=False, repr=False)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def start_attempt(self) -> None:
        """Record the start time of the current attempt."""
        self._attempt_start = time.monotonic()

    def check(self) -> None:
        """Raise :class:`DeadlineExceeded` if any deadline has been breached."""
        now = time.monotonic()
        if self.global_timeout is not None:
            deadline = self._start + self.global_timeout
            if now >= deadline:
                raise DeadlineExceeded("global", deadline, now)
        if self.attempt_timeout is not None and self._attempt_start is not None:
            deadline = self._attempt_start + self.attempt_timeout
            if now >= deadline:
                raise DeadlineExceeded("attempt", deadline, now)

    def global_remaining(self) -> Optional[float]:
        """Seconds remaining in the global budget, or ``None`` if unlimited."""
        if self.global_timeout is None:
            return None
        remaining = (self._start + self.global_timeout) - time.monotonic()
        return max(remaining, 0.0)

    def attempt_remaining(self) -> Optional[float]:
        """Seconds remaining in the current attempt budget, or ``None``."""
        if self.attempt_timeout is None or self._attempt_start is None:
            return None
        remaining = (self._attempt_start + self.attempt_timeout) - time.monotonic()
        return max(remaining, 0.0)

    def elapsed(self) -> float:
        """Total elapsed seconds since the watchdog was created."""
        return time.monotonic() - self._start

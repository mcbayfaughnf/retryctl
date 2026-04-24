"""Execution profiler for retryctl.

Tracks per-attempt timing statistics and produces a summary profile
that can be used for diagnostics and performance tuning.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AttemptProfile:
    """Timing data captured for a single command attempt."""

    attempt: int
    start_time: float
    end_time: Optional[float] = None
    exit_code: Optional[int] = None

    def finish(self, exit_code: int) -> None:
        """Mark the attempt as finished and record its exit code."""
        self.end_time = time.monotonic()
        self.exit_code = exit_code

    @property
    def duration(self) -> Optional[float]:
        """Wall-clock duration of this attempt in seconds, or None if not finished."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "exit_code": self.exit_code,
        }


@dataclass
class ExecutionProfile:
    """Aggregate profile built from all attempt profiles in a run."""

    attempts: List[AttemptProfile] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Derived statistics
    # ------------------------------------------------------------------ #

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    @property
    def total_duration(self) -> float:
        """Sum of all finished attempt durations."""
        return sum(a.duration for a in self.attempts if a.duration is not None)

    @property
    def mean_duration(self) -> Optional[float]:
        """Mean attempt duration, or None if there are no finished attempts."""
        finished = [a.duration for a in self.attempts if a.duration is not None]
        if not finished:
            return None
        return sum(finished) / len(finished)

    @property
    def min_duration(self) -> Optional[float]:
        finished = [a.duration for a in self.attempts if a.duration is not None]
        return min(finished) if finished else None

    @property
    def max_duration(self) -> Optional[float]:
        finished = [a.duration for a in self.attempts if a.duration is not None]
        return max(finished) if finished else None

    def to_dict(self) -> dict:
        return {
            "total_attempts": self.total_attempts,
            "total_duration": self.total_duration,
            "mean_duration": self.mean_duration,
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "attempts": [a.to_dict() for a in self.attempts],
        }


class Profiler:
    """Records timing for each attempt and builds an :class:`ExecutionProfile`."""

    def __init__(self) -> None:
        self._profile = ExecutionProfile()
        self._current: Optional[AttemptProfile] = None

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start_attempt(self, attempt: int) -> None:
        """Begin timing for *attempt* (1-based)."""
        self._current = AttemptProfile(
            attempt=attempt,
            start_time=time.monotonic(),
        )

    def finish_attempt(self, exit_code: int) -> None:
        """Finish the current attempt and add it to the profile."""
        if self._current is None:
            raise RuntimeError("finish_attempt called before start_attempt")
        self._current.finish(exit_code)
        self._profile.attempts.append(self._current)
        self._current = None

    # ------------------------------------------------------------------ #
    # Access
    # ------------------------------------------------------------------ #

    @property
    def profile(self) -> ExecutionProfile:
        """Return the accumulated :class:`ExecutionProfile`."""
        return self._profile

    def reset(self) -> None:
        """Clear all recorded data."""
        self._profile = ExecutionProfile()
        self._current = None

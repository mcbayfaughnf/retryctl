"""Global deadline enforcement across all retry attempts."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


class DeadlineExceeded(Exception):
    def __init__(self, deadline: float, now: float) -> None:
        self.deadline = deadline
        self.now = now
        super().__init__(
            f"Global deadline exceeded: limit={deadline:.2f}s, elapsed={now:.2f}s"
        )


@dataclass
class Deadline:
    """Tracks a wall-clock deadline from the moment it is created."""

    limit: float  # seconds
    _start: float = field(init=False)

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError(f"limit must be positive, got {self.limit}")
        self._start = time.monotonic()

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start

    @property
    def remaining(self) -> float:
        return max(0.0, self.limit - self.elapsed)

    @property
    def expired(self) -> bool:
        return self.elapsed >= self.limit

    def check(self) -> None:
        """Raise DeadlineExceeded if the deadline has passed."""
        elapsed = self.elapsed
        if elapsed >= self.limit:
            raise DeadlineExceeded(deadline=self.limit, now=elapsed)


def maybe_deadline(limit: Optional[float]) -> Optional[Deadline]:
    """Return a Deadline if *limit* is set, otherwise None."""
    if limit is None:
        return None
    return Deadline(limit=limit)

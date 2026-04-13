"""Summary reporter for retry run results."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional

from retryctl.runner import CommandResult


@dataclass
class AttemptRecord:
    """Stores metadata for a single command attempt."""

    attempt: int
    exit_code: int
    duration: float  # seconds
    error: Optional[str] = None


@dataclass
class RunSummary:
    """Aggregated summary of all attempts during a retry run."""

    command: List[str]
    attempts: List[AttemptRecord] = field(default_factory=list)
    succeeded: bool = False
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def record_attempt(self, result: CommandResult, duration: float) -> None:
        """Append the outcome of a single attempt."""
        record = AttemptRecord(
            attempt=result.attempts,
            exit_code=result.exit_code,
            duration=round(duration, 4),
            error=result.stderr.strip() if result.stderr else None,
        )
        self.attempts.append(record)

    def finalise(self, succeeded: bool) -> None:
        """Mark the run as finished."""
        self.succeeded = succeeded
        self.end_time = time.monotonic()

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def total_duration(self) -> float:
        """Wall-clock seconds from start to finish (0 if not finalised)."""
        if self.end_time is None:
            return 0.0
        return round(self.end_time - self.start_time, 4)

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    def to_dict(self) -> dict:
        """Serialise to a plain dictionary (suitable for JSON output)."""
        return {
            "command": self.command,
            "succeeded": self.succeeded,
            "total_attempts": self.total_attempts,
            "total_duration": self.total_duration,
            "attempts": [
                {
                    "attempt": r.attempt,
                    "exit_code": r.exit_code,
                    "duration": r.duration,
                    "error": r.error,
                }
                for r in self.attempts
            ],
        }

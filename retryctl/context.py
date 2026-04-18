"""Run context — carries per-run metadata through the middleware pipeline."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RunContext:
    """Immutable-ish bag of metadata attached to a single retry run."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command: str = ""
    max_attempts: int = 1
    attempt: int = 0
    started_at: float = field(default_factory=time.monotonic)
    labels: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Mutation helpers (return *new* instances to keep things predictable) #
    # ------------------------------------------------------------------ #

    def next_attempt(self) -> "RunContext":
        """Return a copy with attempt incremented by one."""
        import dataclasses
        return dataclasses.replace(self, attempt=self.attempt + 1)

    def with_label(self, key: str, value: str) -> "RunContext":
        """Return a copy with an additional label."""
        import dataclasses
        return dataclasses.replace(self, labels={**self.labels, key: value})

    def with_extra(self, key: str, value: Any) -> "RunContext":
        """Return a copy with an additional extra field."""
        import dataclasses
        return dataclasses.replace(self, extra={**self.extra, key: value})

    # ------------------------------------------------------------------ #

    @property
    def elapsed(self) -> float:
        """Seconds since the run started."""
        return time.monotonic() - self.started_at

    def as_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "command": self.command,
            "max_attempts": self.max_attempts,
            "attempt": self.attempt,
            "elapsed": self.elapsed,
            "labels": dict(self.labels),
            "extra": dict(self.extra),
        }

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RunContext(run_id={self.run_id!r}, command={self.command!r}, "
            f"attempt={self.attempt}/{self.max_attempts})"
        )

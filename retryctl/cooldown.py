"""Per-command cooldown enforcement between retry attempts."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


class CooldownActive(Exception):
    def __init__(self, remaining: float, command: str) -> None:
        self.remaining = remaining
        self.command = command
        super().__init__(
            f"Cooldown active for {command!r}: {remaining:.2f}s remaining"
        )


@dataclass
class CooldownPolicy:
    period: float  # seconds between attempts
    command: str = ""

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")


@dataclass
class CooldownTracker:
    policy: CooldownPolicy
    _last_attempt: Optional[float] = field(default=None, init=False, repr=False)

    def check(self, now: Optional[float] = None) -> None:
        """Raise CooldownActive if the cooldown period has not elapsed."""
        if self._last_attempt is None:
            return
        now = now if now is not None else time.monotonic()
        elapsed = now - self._last_attempt
        if elapsed < self.policy.period:
            raise CooldownActive(
                remaining=self.policy.period - elapsed,
                command=self.policy.command,
            )

    def record(self, now: Optional[float] = None) -> None:
        """Record that an attempt just occurred."""
        self._last_attempt = now if now is not None else time.monotonic()

    def reset(self) -> None:
        self._last_attempt = None

    @property
    def last_attempt(self) -> Optional[float]:
        return self._last_attempt

"""Configuration dataclass for retryctl."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

VALID_STRATEGIES = {"fixed", "linear", "exponential", "jitter"}


@dataclass
class RetryConfig:
    command: list[str]
    max_attempts: int = 3
    strategy: str = "fixed"
    base_delay: float = 1.0
    max_delay: float = 60.0
    increment: float = 1.0
    multiplier: float = 2.0
    jitter_range: float = 0.5
    output_format: str = "text"
    # Per-attempt timeout in seconds; None means no limit.
    attempt_timeout: float | None = None
    # Overall run timeout in seconds; None means no limit.
    overall_timeout: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.strategy not in VALID_STRATEGIES:
            raise ValueError(
                f"Unknown strategy {self.strategy!r}. "
                f"Choose from: {sorted(VALID_STRATEGIES)}"
            )
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.attempt_timeout is not None and self.attempt_timeout <= 0:
            raise ValueError("attempt_timeout must be positive")
        if self.overall_timeout is not None and self.overall_timeout <= 0:
            raise ValueError("overall_timeout must be positive")

    def backoff_kwargs(self) -> dict[str, Any]:
        return {
            "base": self.base_delay,
            "max_delay": self.max_delay,
            "increment": self.increment,
            "multiplier": self.multiplier,
            "jitter_range": self.jitter_range,
        }

"""Configuration dataclass and validation for retryctl."""

from dataclasses import dataclass, field
from typing import List, Optional

from retryctl.backoff import BackoffStrategy


@dataclass
class RetryConfig:
    """Holds all retry-related settings parsed from CLI arguments or defaults."""

    max_attempts: int = 3
    delay: float = 1.0
    multiplier: float = 2.0
    max_delay: float = 60.0
    increment: float = 1.0
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    retry_on_exit_codes: List[int] = field(default_factory=list)
    stop_on_exit_codes: List[int] = field(default_factory=list)
    timeout: Optional[float] = None
    verbose: bool = False

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.delay < 0:
            raise ValueError("delay must be >= 0")
        if self.multiplier < 1:
            raise ValueError("multiplier must be >= 1")
        if self.max_delay < self.delay:
            raise ValueError("max_delay must be >= delay")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be > 0")

    @property
    def backoff_kwargs(self) -> dict:
        """Return keyword arguments suitable for get_backoff_iterator."""
        return {
            "delay": self.delay,
            "multiplier": self.multiplier,
            "max_delay": self.max_delay,
            "increment": self.increment,
        }

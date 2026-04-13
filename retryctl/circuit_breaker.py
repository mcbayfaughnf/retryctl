"""Circuit breaker pattern for retryctl.

Tracks consecutive failures and opens the circuit (stops retrying)
once a configurable threshold is exceeded.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    CLOSED = "closed"      # normal operation
    OPEN = "open"          # blocking calls
    HALF_OPEN = "half_open"  # testing recovery


class CircuitOpenError(Exception):
    """Raised when a call is attempted while the circuit is open."""

    def __init__(self, name: str, reset_at: float) -> None:
        self.name = name
        self.reset_at = reset_at
        remaining = max(0.0, reset_at - time.monotonic())
        super().__init__(
            f"Circuit '{name}' is OPEN; resets in {remaining:.1f}s"
        )


@dataclass
class CircuitBreaker:
    """Tracks failure counts and manages circuit state."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds before moving to HALF_OPEN

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failures: int = field(default=0, init=False)
    _opened_at: Optional[float] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")

    @property
    def state(self) -> CircuitState:
        if self._state is CircuitState.OPEN:
            if time.monotonic() >= self._opened_at + self.recovery_timeout:  # type: ignore[operator]
                self._state = CircuitState.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Return True if a request should be allowed through."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Reset the breaker after a successful call."""
        self._failures = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Increment failure count and open the circuit if threshold reached."""
        self._failures += 1
        if self._state is CircuitState.HALF_OPEN or self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._failures = 0
        self._opened_at = None
        self._state = CircuitState.CLOSED

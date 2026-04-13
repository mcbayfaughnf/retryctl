"""Middleware that integrates CircuitBreaker into the runner pipeline."""
from __future__ import annotations

from typing import Callable

from retryctl.circuit_breaker import CircuitBreaker, CircuitOpenError
from retryctl.runner import CommandResult


class CircuitBreakerMiddleware:
    """Wraps a next-callable with circuit-breaker logic.

    If the circuit is open the middleware raises *CircuitOpenError* instead
    of delegating to *next_fn*, preventing further command execution.
    """

    def __init__(self, breaker: CircuitBreaker, next_fn: Callable[..., CommandResult]) -> None:
        self._breaker = breaker
        self._next = next_fn

    # ------------------------------------------------------------------
    # Callable interface
    # ------------------------------------------------------------------

    def __call__(self, command: list[str], **kwargs) -> CommandResult:  # type: ignore[override]
        if not self._breaker.allow_request():
            raise CircuitOpenError(self._breaker.name, self._breaker._opened_at + self._breaker.recovery_timeout)  # type: ignore[operator]

        result: CommandResult = self._next(command, **kwargs)

        if result.exit_code == 0:
            self._breaker.record_success()
        else:
            self._breaker.record_failure()

        return result

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Manually reset the underlying circuit breaker."""
        self._breaker.reset()

    @property
    def state(self):
        return self._breaker.state

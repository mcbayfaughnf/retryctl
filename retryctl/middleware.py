"""Middleware pipeline for retryctl.

Allows pluggable callables to be inserted around each attempt so that
cross-cutting concerns (throttling, metrics, dry-run mode, …) can be
composed without modifying the core runner.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from retryctl.runner import CommandResult

# A middleware is a callable that receives the *next* handler and the
# attempt number, and returns a CommandResult.
AttemptHandler = Callable[[int], CommandResult]
MiddlewareFn = Callable[[AttemptHandler, int], CommandResult]


class MiddlewarePipeline:
    """Ordered chain of middleware functions wrapping an inner handler.

    Usage::

        pipeline = MiddlewarePipeline(inner=run_attempt)
        pipeline.add(my_middleware)
        result = pipeline(attempt=1)
    """

    def __init__(self, inner: AttemptHandler) -> None:
        self._inner = inner
        self._middlewares: List[MiddlewareFn] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add(self, middleware: MiddlewareFn) -> "MiddlewarePipeline":
        """Append *middleware* to the pipeline; returns *self* for chaining."""
        self._middlewares.append(middleware)
        return self

    def remove(self, middleware: MiddlewareFn) -> None:
        """Remove the first occurrence of *middleware* (raises if absent)."""
        self._middlewares.remove(middleware)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def __call__(self, attempt: int) -> CommandResult:
        """Execute the pipeline for the given *attempt* number."""
        handler = self._build(0)
        return handler(attempt)

    def _build(self, index: int) -> AttemptHandler:
        if index >= len(self._middlewares):
            return self._inner
        mw = self._middlewares[index]
        next_handler = self._build(index + 1)
        return lambda attempt: mw(next_handler, attempt)


# ---------------------------------------------------------------------------
# Built-in middleware factories
# ---------------------------------------------------------------------------

def throttle_middleware(bucket) -> MiddlewareFn:  # type: ignore[type-arg]
    """Return middleware that consumes one token from *bucket* before each
    attempt, blocking until a token is available.
    """

    def _middleware(next_handler: AttemptHandler, attempt: int) -> CommandResult:
        bucket.consume(block=True)
        return next_handler(attempt)

    _middleware.__name__ = "throttle_middleware"
    return _middleware


def dry_run_middleware(command: str) -> MiddlewareFn:
    """Return middleware that short-circuits execution and returns a
    synthetic success result without running the real command.
    """

    def _middleware(next_handler: AttemptHandler, attempt: int) -> CommandResult:
        return CommandResult(
            command=command,
            exit_code=0,
            stdout="[dry-run]",
            stderr="",
            attempts=attempt,
            duration=0.0,
        )

    _middleware.__name__ = "dry_run_middleware"
    return _middleware

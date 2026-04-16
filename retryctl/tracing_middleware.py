"""Middleware that records a tracing span for every command attempt."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.runner import CommandResult
from retryctl.tracing import Span, Tracer


class TracingMiddleware:
    """Wraps each attempt in a tracing span."""

    def __init__(self, tracer: Optional[Tracer] = None) -> None:
        self._tracer: Tracer = tracer or Tracer()

    def __call__(self, result: CommandResult, next: Callable) -> CommandResult:
        span: Span = self._tracer.start_span(
            name="attempt",
            parent_id=None,
        )
        span.set("command", " ".join(result.command) if result.command else "")
        span.set("attempt", result.attempts)
        try:
            outcome: CommandResult = next(result)
        except Exception as exc:
            span.set("error", str(exc))
            span.finish()
            raise
        span.set("exit_code", outcome.exit_code)
        span.set("success", outcome.exit_code == 0)
        span.finish()
        return outcome

    @property
    def tracer(self) -> Tracer:
        return self._tracer

    def reset(self) -> None:
        self._tracer.reset()

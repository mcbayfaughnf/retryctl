"""Tee middleware — duplicates each attempt result to one or more sink callables.

Useful for forwarding results to external systems (logging, metrics, alerting)
without affecting the main execution pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from retryctl.runner import CommandResult


Sink = Callable[[CommandResult], None]


class TeeError(Exception):
    """Raised when a sink raises and strict mode is enabled."""

    def __init__(self, sink: Sink, cause: Exception) -> None:
        self.sink = sink
        self.cause = cause
        super().__init__(f"Tee sink {sink!r} raised: {cause}")


@dataclass
class TeeMiddleware:
    """Forwards every result to registered sinks before returning it upstream.

    Parameters
    ----------
    sinks:
        Callables that receive a :class:`~retryctl.runner.CommandResult`.
    strict:
        When *True* any exception raised by a sink is re-raised as
        :class:`TeeError`.  When *False* (default) sink errors are silently
        swallowed so they never interrupt the retry loop.
    """

    sinks: List[Sink] = field(default_factory=list)
    strict: bool = False

    def __post_init__(self) -> None:
        self._sinks: List[Sink] = list(self.sinks)

    # ------------------------------------------------------------------
    # Middleware protocol
    # ------------------------------------------------------------------

    def __call__(self, result: CommandResult, next: Callable[[CommandResult], CommandResult]) -> CommandResult:
        outcome = next(result)
        for sink in self._sinks:
            try:
                sink(outcome)
            except Exception as exc:  # noqa: BLE001
                if self.strict:
                    raise TeeError(sink, exc) from exc
        return outcome

    # ------------------------------------------------------------------
    # Sink management
    # ------------------------------------------------------------------

    def add_sink(self, sink: Sink) -> None:
        """Register a new sink."""
        if sink not in self._sinks:
            self._sinks.append(sink)

    def remove_sink(self, sink: Sink) -> None:
        """Unregister a sink (no-op if not present)."""
        try:
            self._sinks.remove(sink)
        except ValueError:
            pass

    @property
    def sink_count(self) -> int:
        """Number of currently registered sinks."""
        return len(self._sinks)

    def reset(self) -> None:
        """Remove all sinks."""
        self._sinks.clear()

"""Wire the SignalBus to the existing Hooks and Reporter subsystems.

Call ``attach_defaults(bus, hooks, summary)`` once during startup so that
all lifecycle events emitted on *bus* are automatically forwarded to the
hooks callbacks and recorded in the run summary.
"""
from __future__ import annotations

from typing import Optional

from retryctl.hooks import RetryHooks
from retryctl.reporter import RunSummary, record_attempt
from retryctl.runner import CommandResult
from retryctl.signals import (
    EVENT_FAILURE,
    EVENT_RETRY,
    EVENT_START,
    EVENT_SUCCESS,
    SignalBus,
)


def attach_defaults(
    bus: SignalBus,
    hooks: RetryHooks,
    summary: Optional[RunSummary] = None,
) -> None:
    """Register default handlers on *bus* for hooks and optional reporter.

    Parameters
    ----------
    bus:
        The :class:`~retryctl.signals.SignalBus` to attach handlers to.
    hooks:
        The :class:`~retryctl.hooks.RetryHooks` instance whose callbacks
        should be invoked on matching events.
    summary:
        Optional :class:`~retryctl.reporter.RunSummary` that will receive
        attempt records on every ``retry`` / ``success`` / ``failure`` event.
    """

    def _on_start(**kwargs: object) -> None:
        hooks.fire_start()

    def _on_retry(**kwargs: object) -> None:
        result: CommandResult = kwargs["result"]  # type: ignore[assignment]
        attempt: int = int(kwargs.get("attempt", 0))
        delay: float = float(kwargs.get("delay", 0.0))
        hooks.fire_retry(result=result, attempt=attempt, delay=delay)
        if summary is not None:
            record_attempt(summary, result=result, attempt=attempt, delay=delay)

    def _on_success(**kwargs: object) -> None:
        result: CommandResult = kwargs["result"]  # type: ignore[assignment]
        hooks.fire_success(result=result)
        if summary is not None:
            attempt: int = int(kwargs.get("attempt", 0))
            record_attempt(summary, result=result, attempt=attempt, delay=0.0)

    def _on_failure(**kwargs: object) -> None:
        result: CommandResult = kwargs["result"]  # type: ignore[assignment]
        hooks.fire_failure(result=result)
        if summary is not None:
            attempt: int = int(kwargs.get("attempt", 0))
            record_attempt(summary, result=result, attempt=attempt, delay=0.0)

    bus.on(EVENT_START, _on_start)
    bus.on(EVENT_RETRY, _on_retry)
    bus.on(EVENT_SUCCESS, _on_success)
    bus.on(EVENT_FAILURE, _on_failure)

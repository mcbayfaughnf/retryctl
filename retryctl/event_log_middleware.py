"""Middleware that records attempt/success/failure events into an EventLog."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.event_log import EventLog
from retryctl.runner import CommandResult


class EventLogMiddleware:
    """Records attempt outcomes into a shared EventLog instance."""

    def __init__(self, log: Optional[EventLog] = None) -> None:
        self._log = log if log is not None else EventLog()

    def __call__(self, result: CommandResult, next: Callable[[CommandResult], CommandResult]) -> CommandResult:
        attempt = result.attempts
        self._log.record("attempt", attempt=attempt)
        outcome = next(result)
        if outcome.exit_code == 0:
            self._log.record("success", attempt=attempt, data={"exit_code": outcome.exit_code})
        else:
            self._log.record(
                "failure",
                attempt=attempt,
                data={"exit_code": outcome.exit_code},
            )
        return outcome

    @property
    def log(self) -> EventLog:
        return self._log

    def reset(self) -> None:
        self._log.clear()

"""Dry-run middleware: simulates command execution without side-effects."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from retryctl.runner import CommandResult


@dataclass
class DryRunRecord:
    """Records a single simulated invocation."""

    command: List[str]
    attempt: int
    simulated_exit_code: int = 0

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"DryRunRecord(command={self.command!r}, "
            f"attempt={self.attempt}, "
            f"exit_code={self.simulated_exit_code})"
        )


class DryRunMiddleware:
    """Middleware that intercepts execution and returns a fake result.

    When *enabled* the wrapped callable is never invoked; instead a
    :class:`CommandResult` with the configured *exit_code* is returned and
    the invocation is appended to :attr:`records` for inspection.

    Parameters
    ----------
    exit_code:
        The exit code the simulated result will carry.  Defaults to ``0``.
    enabled:
        Toggle dry-run mode at construction time.  Defaults to ``True``.
    """

    def __init__(self, exit_code: int = 0, enabled: bool = True) -> None:
        if not isinstance(exit_code, int):
            raise TypeError("exit_code must be an int")
        self.exit_code = exit_code
        self.enabled = enabled
        self.records: List[DryRunRecord] = []
        self._attempt = 0

    # ------------------------------------------------------------------
    # Middleware protocol
    # ------------------------------------------------------------------

    def __call__(
        self,
        next_call: Callable[..., CommandResult],
        command: List[str],
        **kwargs,
    ) -> CommandResult:
        """Intercept *command* when dry-run is enabled."""
        if not self.enabled:
            return next_call(command, **kwargs)

        self._attempt += 1
        record = DryRunRecord(
            command=list(command),
            attempt=self._attempt,
            simulated_exit_code=self.exit_code,
        )
        self.records.append(record)

        return CommandResult(
            command=command,
            exit_code=self.exit_code,
            stdout="[dry-run]",
            stderr="",
            attempts=self._attempt,
            elapsed=0.0,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear recorded invocations and reset the attempt counter."""
        self.records.clear()
        self._attempt = 0

    @property
    def call_count(self) -> int:
        """Number of simulated invocations since the last :meth:`reset`."""
        return len(self.records)

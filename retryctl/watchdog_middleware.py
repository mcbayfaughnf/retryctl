"""Middleware that enforces Watchdog deadlines around each command attempt."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.runner import CommandResult
from retryctl.watchdog import DeadlineExceeded, Watchdog


class WatchdogMiddleware:
    """Wraps the next handler with watchdog deadline checks.

    The middleware:
    1. Calls ``watchdog.start_attempt()`` before delegating.
    2. Calls ``watchdog.check()`` after the attempt returns so that a
       deadline breach that occurred *during* execution is surfaced.
    3. Re-raises :class:`~retryctl.watchdog.DeadlineExceeded` unchanged so
       that the runner can treat it as a terminal condition.

    Parameters
    ----------
    watchdog:
        A :class:`~retryctl.watchdog.Watchdog` instance shared across all
        attempts in a single run.
    next_handler:
        The callable to delegate to (the inner pipeline or the real runner).
    """

    def __init__(
        self,
        watchdog: Watchdog,
        next_handler: Callable[..., CommandResult],
    ) -> None:
        self._watchdog = watchdog
        self._next = next_handler

    # ------------------------------------------------------------------

    def __call__(self, command: list[str], attempt: int, **kwargs) -> CommandResult:
        # Check *before* starting — the global budget may already be gone.
        self._watchdog.check()
        self._watchdog.start_attempt()
        try:
            result = self._next(command, attempt, **kwargs)
        except DeadlineExceeded:
            raise
        # Surface a deadline that was crossed during execution.
        self._watchdog.check()
        return result

    # ------------------------------------------------------------------

    @property
    def watchdog(self) -> Watchdog:
        """Expose the underlying watchdog for inspection."""
        return self._watchdog

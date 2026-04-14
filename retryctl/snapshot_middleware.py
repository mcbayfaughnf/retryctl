"""Middleware that records an OutputSnapshot after every attempt."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.runner import CommandResult
from retryctl.snapshot import OutputSnapshot, SnapshotHistory


class SnapshotMiddleware:
    """Wraps a next-handler to build a SnapshotHistory across retries.

    Parameters
    ----------
    next_handler:
        The next callable in the middleware pipeline.
    history:
        Optional pre-existing history; a fresh one is created when omitted.
    on_change:
        Optional callback invoked with the history whenever output changes
        between consecutive attempts.
    """

    def __init__(
        self,
        next_handler: Callable[..., CommandResult],
        history: Optional[SnapshotHistory] = None,
        on_change: Optional[Callable[[SnapshotHistory], None]] = None,
    ) -> None:
        self._next = next_handler
        self.history: SnapshotHistory = history if history is not None else SnapshotHistory()
        self._on_change = on_change

    def __call__(self, attempt: int, **kwargs) -> CommandResult:
        result: CommandResult = self._next(attempt=attempt, **kwargs)

        snap = OutputSnapshot(
            attempt=attempt,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.exit_code,
        )
        self.history.record(snap)

        if self.history.output_changed() and self._on_change is not None:
            self._on_change(self.history)

        return result

    def reset(self) -> None:
        """Clear the accumulated history (useful between independent runs)."""
        self.history = SnapshotHistory()

"""Middleware that saves/restores attempt progress via CheckpointStore."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.checkpoint import CheckpointData, CheckpointStore
from retryctl.runner import CommandResult


class CheckpointMiddleware:
    """Persist attempt number and last exit code between invocations.

    On construction the store is queried; if a checkpoint exists the
    attempt counter is fast-forwarded so the run effectively resumes.
    The checkpoint is cleared automatically on success.
    """

    def __init__(self, store: CheckpointStore, command: str) -> None:
        self._store = store
        self._command = command
        existing = store.load()
        self._resume_from: int = existing.attempt if existing else 1

    # ------------------------------------------------------------------
    def __call__(self, next_fn: Callable[..., CommandResult], *args, **kwargs) -> CommandResult:
        result: CommandResult = next_fn(*args, **kwargs)
        attempt = kwargs.get("attempt", self._resume_from)
        if result.exit_code == 0:
            self._store.clear()
        else:
            self._store.save(
                CheckpointData(
                    command=self._command,
                    attempt=attempt,
                    last_exit_code=result.exit_code,
                )
            )
        return result

    # ------------------------------------------------------------------
    @property
    def resume_from(self) -> int:
        """Attempt number to resume from (1 if no checkpoint exists)."""
        return self._resume_from

    def clear(self) -> None:
        self._store.clear()
        self._resume_from = 1

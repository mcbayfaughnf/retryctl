"""Replay middleware – re-run the last successful result from a recorded
history instead of executing the real command when a replay is requested."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from retryctl.runner import CommandResult


class ReplayError(Exception):
    """Raised when a replay is requested but no history is available."""

    def __init__(self, message: str = "No recorded result available for replay") -> None:
        super().__init__(message)
        self.message = message


@dataclass
class ReplayStore:
    """Holds the most-recent successful :class:`CommandResult` for replay."""

    _history: List[CommandResult] = field(default_factory=list, init=False)
    max_size: int = 10

    def __post_init__(self) -> None:
        if self.max_size < 1:
            raise ValueError("max_size must be >= 1")

    def record(self, result: CommandResult) -> None:
        """Append *result* to the history, evicting the oldest entry if needed."""
        self._history.append(result)
        if len(self._history) > self.max_size:
            self._history.pop(0)

    def latest(self) -> CommandResult:
        """Return the most-recently recorded result.

        Raises :class:`ReplayError` when the store is empty.
        """
        if not self._history:
            raise ReplayError()
        return self._history[-1]

    def clear(self) -> None:
        """Remove all recorded results."""
        self._history.clear()

    @property
    def size(self) -> int:
        return len(self._history)


class ReplayMiddleware:
    """Middleware that short-circuits execution and returns a previously
    recorded result when *replay* mode is active."""

    def __init__(
        self,
        store: Optional[ReplayStore] = None,
        *,
        replay: bool = False,
        record_successes: bool = True,
    ) -> None:
        self._store = store if store is not None else ReplayStore()
        self._replay = replay
        self._record_successes = record_successes

    def __call__(
        self, next_fn: Callable[..., CommandResult], *args: object, **kwargs: object
    ) -> CommandResult:
        if self._replay:
            return self._store.latest()

        result = next_fn(*args, **kwargs)

        if self._record_successes and result.exit_code == 0:
            self._store.record(result)

        return result

    def enable_replay(self) -> None:
        self._replay = True

    def disable_replay(self) -> None:
        self._replay = False

    @property
    def store(self) -> ReplayStore:
        return self._store

    @property
    def replaying(self) -> bool:
        return self._replay

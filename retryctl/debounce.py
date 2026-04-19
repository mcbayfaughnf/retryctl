"""Debounce middleware: suppress duplicate commands within a quiet window."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from retryctl.runner import CommandResult


class DebounceActive(Exception):
    """Raised when a command is debounced (too soon after the last run)."""

    def __init__(self, command: str, remaining: float) -> None:
        self.command = command
        self.remaining = remaining
        super().__init__(
            f"Command {command!r} is debounced; {remaining:.3f}s remaining in quiet window"
        )


@dataclass
class DebounceTracker:
    """Tracks last-run timestamps per command key."""

    window: float  # seconds
    _last: Dict[str, float] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError("window must be positive")

    def check(self, key: str) -> None:
        """Raise DebounceActive if the key was seen within the quiet window."""
        now = time.monotonic()
        last = self._last.get(key)
        if last is not None:
            elapsed = now - last
            if elapsed < self.window:
                raise DebounceActive(key, self.window - elapsed)

    def record(self, key: str) -> None:
        """Record that the command ran now."""
        self._last[key] = time.monotonic()

    def reset(self, key: Optional[str] = None) -> None:
        """Clear one key or all keys."""
        if key is None:
            self._last.clear()
        else:
            self._last.pop(key, None)


class DebounceMiddleware:
    """Middleware that prevents the same command from running too frequently."""

    def __init__(self, window: float, key_fn: Optional[Callable[[str], str]] = None) -> None:
        self._tracker = DebounceTracker(window=window)
        self._key_fn = key_fn or (lambda cmd: cmd)

    def __call__(self, command: str, next_fn: Callable[[str], CommandResult]) -> CommandResult:
        key = self._key_fn(command)
        self._tracker.check(key)
        result = next_fn(command)
        self._tracker.record(key)
        return result

    def reset(self, key: Optional[str] = None) -> None:
        self._tracker.reset(key)

    @property
    def tracker(self) -> DebounceTracker:
        return self._tracker

"""Middleware that enforces a global deadline across all retry attempts."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.deadline import Deadline, DeadlineExceeded, maybe_deadline
from retryctl.runner import CommandResult


class DeadlineMiddleware:
    """Wraps a next-callable and checks a global deadline before each attempt."""

    def __init__(self, limit: Optional[float] = None, *, _deadline: Optional[Deadline] = None) -> None:
        if _deadline is not None:
            self._deadline: Optional[Deadline] = _deadline
        else:
            self._deadline = maybe_deadline(limit)

    def __call__(self, next_fn: Callable[[], CommandResult]) -> CommandResult:
        if self._deadline is not None:
            self._deadline.check()
        return next_fn()

    @property
    def deadline(self) -> Optional[Deadline]:
        return self._deadline

    @property
    def remaining(self) -> Optional[float]:
        if self._deadline is None:
            return None
        return self._deadline.remaining

    @property
    def expired(self) -> bool:
        if self._deadline is None:
            return False
        return self._deadline.expired

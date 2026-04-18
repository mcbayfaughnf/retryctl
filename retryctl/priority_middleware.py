"""Middleware that assigns and records attempt priority via PriorityQueue."""
from __future__ import annotations

from typing import Callable

from retryctl.priority import PriorityQueue, PriorityEntry
from retryctl.runner import CommandResult


class PriorityMiddleware:
    """Wraps each attempt invocation in a priority entry.

    The priority can be determined dynamically via a resolver callable
    that receives the current attempt number, or set as a fixed value.
    """

    def __init__(
        self,
        resolver: Callable[[int], int] | None = None,
        fixed_priority: int = 0,
    ) -> None:
        self._resolver = resolver
        self._fixed = fixed_priority
        self._queue: PriorityQueue = PriorityQueue()
        self._attempt: int = 0

    def __call__(self, next_fn: Callable[[], CommandResult]) -> CommandResult:
        priority = (
            self._resolver(self._attempt)
            if self._resolver is not None
            else self._fixed
        )
        entry: PriorityEntry = self._queue.push(
            payload={"attempt": self._attempt, "priority": priority},
            priority=priority,
        )
        self._attempt += 1
        result = next_fn()
        result.extra["priority_entry"] = entry  # type: ignore[attr-defined]
        return result

    @property
    def queue(self) -> PriorityQueue:
        return self._queue

    def reset(self) -> None:
        self._queue = PriorityQueue()
        self._attempt = 0

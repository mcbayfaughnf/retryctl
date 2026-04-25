"""Middleware that enforces bulkhead isolation for command execution."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.bulkhead import BulkheadPartition, get_or_create
from retryctl.runner import CommandResult


class BulkheadMiddleware:
    """Wraps a next-callable with bulkhead capacity enforcement.

    If the partition is full, ``BulkheadFull`` propagates to the caller.
    The slot is always released after *next* returns, even on exception.
    """

    def __init__(
        self,
        partition: Optional[BulkheadPartition] = None,
        *,
        name: str = "default",
        limit: int = 10,
    ) -> None:
        self._partition = partition or get_or_create(name, limit)

    def __call__(
        self, next: Callable[[], CommandResult], /
    ) -> CommandResult:
        self._partition.acquire()
        try:
            return next()
        finally:
            self._partition.release()

    @property
    def partition(self) -> BulkheadPartition:
        return self._partition

    @property
    def active(self) -> int:
        return self._partition.active

    @property
    def available(self) -> int:
        return self._partition.available

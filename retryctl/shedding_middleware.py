"""Middleware that enforces load-shedding via SheddingTracker."""
from __future__ import annotations

from typing import Callable

from retryctl.runner import CommandResult
from retryctl.shedding import LoadShedded, SheddingPolicy, SheddingTracker


class SheddingMiddleware:
    """Drop the attempt when load exceeds the configured threshold."""

    def __init__(self, policy: SheddingPolicy) -> None:
        self._tracker = SheddingTracker(policy=policy)

    def __call__(self, next_fn: Callable[[], CommandResult]) -> CommandResult:
        load = self._tracker.current_load()
        if self._tracker.should_shed():
            raise LoadShedded(load=load, threshold=self._tracker.policy.threshold)
        result = next_fn()
        self._tracker.record(success=result.exit_code == 0)
        return result

    @property
    def tracker(self) -> SheddingTracker:
        return self._tracker

    def reset(self) -> None:
        self._tracker.reset()

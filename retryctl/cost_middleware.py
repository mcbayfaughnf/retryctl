"""Middleware that charges cost per attempt and blocks when budget is exhausted."""
from __future__ import annotations
from typing import Callable, Optional
from retryctl.cost import CostAccumulator, CostPolicy, CostExceeded
from retryctl.runner import CommandResult


class CostMiddleware:
    """Wraps a next-callable and deducts cost before each attempt."""

    def __init__(
        self,
        policy: Optional[CostPolicy] = None,
        *,
        cost_per_attempt: float = 1.0,
        budget: Optional[float] = None,
    ) -> None:
        if policy is None:
            policy = CostPolicy(cost_per_attempt=cost_per_attempt, budget=budget)
        self._accumulator = CostAccumulator(policy=policy)

    def __call__(self, next_fn: Callable[[], CommandResult]) -> CommandResult:
        self._accumulator.charge()
        return next_fn()

    @property
    def total_cost(self) -> float:
        return self._accumulator.total

    def remaining(self):
        return self._accumulator.remaining()

    def reset(self) -> None:
        self._accumulator.reset()

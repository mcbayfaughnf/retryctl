"""Middleware that enforces a QuotaBudget before each attempt."""
from __future__ import annotations

from typing import Callable, Optional

from retryctl.quota_budget import QuotaBudget, QuotaBudgetPolicy
from retryctl.runner import CommandResult


class QuotaBudgetMiddleware:
    """Wraps a command callable with quota-budget enforcement."""

    def __init__(
        self,
        policy: Optional[QuotaBudgetPolicy] = None,
        *,
        max_attempts: int = 10,
        max_cost: float = 0.0,
        cost_per_attempt: float = 1.0,
    ) -> None:
        if policy is None:
            policy = QuotaBudgetPolicy(
                max_attempts=max_attempts,
                max_cost=max_cost,
                cost_per_attempt=cost_per_attempt,
            )
        self._budget = QuotaBudget(policy=policy)

    def __call__(
        self, next_fn: Callable[..., CommandResult], *args, **kwargs
    ) -> CommandResult:
        self._budget.consume()  # raises QuotaBudgetExhausted if over limit
        return next_fn(*args, **kwargs)

    @property
    def budget(self) -> QuotaBudget:
        return self._budget

    @property
    def attempts(self) -> int:
        return self._budget.attempts

    @property
    def total_cost(self) -> float:
        return self._budget.total_cost

    def remaining(self):
        return self._budget.remaining()

    def reset(self) -> None:
        self._budget.reset()

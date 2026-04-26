"""Quota-aware retry budget that combines sliding-window quota with a
per-run cost cap, refusing further attempts when either limit is hit."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class QuotaBudgetExhausted(Exception):
    """Raised when the quota budget refuses a new attempt."""

    def __init__(self, reason: str, used: int, limit: int) -> None:
        self.reason = reason
        self.used = used
        self.limit = limit
        super().__init__(f"QuotaBudget exhausted ({reason}): {used}/{limit}")


@dataclass
class QuotaBudgetPolicy:
    """Configuration for a QuotaBudget."""

    max_attempts: int          # hard cap on total attempts in this run
    max_cost: float = 0.0      # optional cumulative cost cap (0 = disabled)
    cost_per_attempt: float = 1.0

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if self.max_cost < 0:
            raise ValueError("max_cost must be non-negative")
        if self.cost_per_attempt <= 0:
            raise ValueError("cost_per_attempt must be positive")


@dataclass
class QuotaBudget:
    """Stateful counter that enforces a QuotaBudgetPolicy."""

    policy: QuotaBudgetPolicy
    _attempts: int = field(default=0, init=False)
    _cost: float = field(default=0.0, init=False)

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def total_cost(self) -> float:
        return self._cost

    def consume(self) -> None:
        """Record one attempt, raising QuotaBudgetExhausted if over limit."""
        if self._attempts >= self.policy.max_attempts:
            raise QuotaBudgetExhausted(
                "attempt limit", self._attempts, self.policy.max_attempts
            )
        projected_cost = self._cost + self.policy.cost_per_attempt
        if self.policy.max_cost > 0 and projected_cost > self.policy.max_cost:
            raise QuotaBudgetExhausted(
                "cost limit",
                int(self._cost),
                int(self.policy.max_cost),
            )
        self._attempts += 1
        self._cost += self.policy.cost_per_attempt

    def remaining(self) -> Optional[int]:
        """Attempts remaining under the attempt cap."""
        return max(0, self.policy.max_attempts - self._attempts)

    def reset(self) -> None:
        self._attempts = 0
        self._cost = 0.0

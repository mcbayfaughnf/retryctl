"""Per-attempt cost tracking with a configurable budget cap."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


class CostExceeded(Exception):
    def __init__(self, used: float, limit: float) -> None:
        self.used = used
        self.limit = limit
        super().__init__(f"cost budget exceeded: used={used:.4f} limit={limit:.4f}")


@dataclass
class CostPolicy:
    """Assigns a cost to each attempt and enforces a total budget."""
    cost_per_attempt: float = 1.0
    budget: Optional[float] = None

    def __post_init__(self) -> None:
        if self.cost_per_attempt < 0:
            raise ValueError("cost_per_attempt must be >= 0")
        if self.budget is not None and self.budget <= 0:
            raise ValueError("budget must be > 0")


@dataclass
class CostAccumulator:
    """Tracks cumulative cost across attempts."""
    policy: CostPolicy
    _total: float = field(default=0.0, init=False)

    @property
    def total(self) -> float:
        return self._total

    def charge(self, multiplier: float = 1.0) -> float:
        """Charge one attempt worth of cost; raise CostExceeded if over budget."""
        amount = self.policy.cost_per_attempt * multiplier
        projected = self._total + amount
        if self.policy.budget is not None and projected > self.policy.budget:
            raise CostExceeded(used=projected, limit=self.policy.budget)
        self._total = projected
        return amount

    def reset(self) -> None:
        self._total = 0.0

    def remaining(self) -> Optional[float]:
        if self.policy.budget is None:
            return None
        return max(0.0, self.policy.budget - self._total)

"""Global registry for named QuotaBudget instances."""
from __future__ import annotations

from typing import Dict, Optional

from retryctl.quota_budget import QuotaBudget, QuotaBudgetPolicy

_registry: Dict[str, QuotaBudget] = {}


def get_or_create(
    name: str,
    max_attempts: int = 10,
    max_cost: float = 0.0,
    cost_per_attempt: float = 1.0,
) -> QuotaBudget:
    """Return an existing budget by name or create and register a new one."""
    if name not in _registry:
        policy = QuotaBudgetPolicy(
            max_attempts=max_attempts,
            max_cost=max_cost,
            cost_per_attempt=cost_per_attempt,
        )
        _registry[name] = QuotaBudget(policy=policy)
    return _registry[name]


def get(name: str) -> Optional[QuotaBudget]:
    return _registry.get(name)


def register(name: str, budget: QuotaBudget) -> None:
    _registry[name] = budget


def remove(name: str) -> None:
    _registry.pop(name, None)


def reset_all() -> None:
    """Reset counters on every registered budget (useful between test runs)."""
    for budget in _registry.values():
        budget.reset()


def clear() -> None:
    _registry.clear()

"""Global registry of named CostAccumulator instances."""
from __future__ import annotations
from typing import Dict, Optional
from retryctl.cost import CostAccumulator, CostPolicy

_registry: Dict[str, CostAccumulator] = {}


def get_or_create(
    name: str,
    *,
    cost_per_attempt: float = 1.0,
    budget: Optional[float] = None,
) -> CostAccumulator:
    if name not in _registry:
        policy = CostPolicy(cost_per_attempt=cost_per_attempt, budget=budget)
        _registry[name] = CostAccumulator(policy=policy)
    return _registry[name]


def get(name: str) -> Optional[CostAccumulator]:
    return _registry.get(name)


def reset(name: str) -> None:
    if name in _registry:
        _registry[name].reset()


def remove(name: str) -> None:
    _registry.pop(name, None)


def reset_all() -> None:
    for acc in _registry.values():
        acc.reset()

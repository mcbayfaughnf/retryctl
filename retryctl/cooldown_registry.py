"""Global registry of named CooldownTracker instances."""
from __future__ import annotations

from typing import Dict, Optional

from retryctl.cooldown import CooldownPolicy, CooldownTracker

_registry: Dict[str, CooldownTracker] = {}


def get_or_create(name: str, period: float) -> CooldownTracker:
    if name not in _registry:
        policy = CooldownPolicy(period=period, command=name)
        _registry[name] = CooldownTracker(policy=policy)
    return _registry[name]


def get(name: str) -> Optional[CooldownTracker]:
    return _registry.get(name)


def reset(name: str) -> None:
    if name in _registry:
        _registry[name].reset()


def remove(name: str) -> None:
    _registry.pop(name, None)


def reset_all() -> None:
    for tracker in _registry.values():
        tracker.reset()
    _registry.clear()

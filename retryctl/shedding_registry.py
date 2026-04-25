"""Global registry for named SheddingTracker instances."""
from __future__ import annotations

from typing import Dict, Optional

from retryctl.shedding import SheddingPolicy, SheddingTracker

_registry: Dict[str, SheddingTracker] = {}


def get_or_create(
    name: str,
    threshold: float = 0.8,
    window: float = 5.0,
) -> SheddingTracker:
    if name not in _registry:
        policy = SheddingPolicy(threshold=threshold, window=window)
        _registry[name] = SheddingTracker(policy=policy)
    return _registry[name]


def get(name: str) -> Optional[SheddingTracker]:
    return _registry.get(name)


def reset(name: str) -> None:
    if name in _registry:
        _registry[name].reset()


def remove(name: str) -> None:
    _registry.pop(name, None)


def reset_all() -> None:
    _registry.clear()

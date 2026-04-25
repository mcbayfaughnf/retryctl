"""Global registry for :class:`~retryctl.replay.ReplayStore` instances,
keyed by an arbitrary string name.  Mirrors the pattern used by other
registries in the project (circuit_breaker_registry, quota_registry, etc.).
"""
from __future__ import annotations

from typing import Dict, Optional

from retryctl.replay import ReplayStore

_stores: Dict[str, ReplayStore] = {}


def get_or_create(name: str, *, max_size: int = 10) -> ReplayStore:
    """Return the named store, creating it with *max_size* if absent."""
    if name not in _stores:
        _stores[name] = ReplayStore(max_size=max_size)
    return _stores[name]


def get(name: str) -> Optional[ReplayStore]:
    """Return the named store, or *None* if it does not exist."""
    return _stores.get(name)


def register(name: str, store: ReplayStore) -> None:
    """Register an externally-created *store* under *name*.

    Raises :class:`KeyError` if the name is already taken.
    """
    if name in _stores:
        raise KeyError(f"A ReplayStore named {name!r} is already registered")
    _stores[name] = store


def remove(name: str) -> None:
    """Remove the named store if it exists (no-op otherwise)."""
    _stores.pop(name, None)


def reset_all() -> None:
    """Clear every registered store (useful in tests)."""
    _stores.clear()


def names() -> list[str]:
    """Return a sorted list of all registered store names."""
    return sorted(_stores.keys())

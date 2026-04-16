"""Global singleton registry for quota counters."""
from __future__ import annotations
from typing import Optional
from retryctl.quota import QuotaCounter, QuotaRegistry

_registry = QuotaRegistry()


def get_or_create(key: str, limit: int, window: float) -> QuotaCounter:
    """Return existing counter or create one for *key*."""
    return _registry.get_or_create(key, limit, window)


def get(key: str) -> Optional[QuotaCounter]:
    """Return counter for *key* or None if not registered."""
    return _registry._counters.get(key)


def reset(key: Optional[str] = None) -> None:
    """Reset one or all counters."""
    _registry.reset(key)


def remove(key: str) -> None:
    """Remove counter for *key* from the global registry."""
    _registry.remove(key)


def reset_all() -> None:
    """Convenience alias – reset every counter."""
    _registry.reset()

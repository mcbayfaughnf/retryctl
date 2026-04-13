"""Global registry for named CircuitBreaker instances.

Allows different parts of the application (CLI, integration layer, tests)
to share a single breaker per logical service name.
"""
from __future__ import annotations

from typing import Dict, Optional

from retryctl.circuit_breaker import CircuitBreaker

_registry: Dict[str, CircuitBreaker] = {}


def get_or_create(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    """Return the existing breaker for *name* or create and register a new one."""
    if name not in _registry:
        _registry[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _registry[name]


def get(name: str) -> Optional[CircuitBreaker]:
    """Return the breaker registered under *name*, or None."""
    return _registry.get(name)


def register(breaker: CircuitBreaker) -> None:
    """Explicitly register a pre-built CircuitBreaker instance."""
    _registry[breaker.name] = breaker


def remove(name: str) -> None:
    """Remove a breaker from the registry (useful in tests)."""
    _registry.pop(name, None)


def reset_all() -> None:
    """Reset every registered breaker to CLOSED state."""
    for breaker in _registry.values():
        breaker.reset()


def clear() -> None:
    """Remove all entries from the registry."""
    _registry.clear()


def available() -> list[str]:
    """Return a sorted list of registered breaker names."""
    return sorted(_registry.keys())

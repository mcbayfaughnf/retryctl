"""Global registry for named FallbackPolicy instances."""
from __future__ import annotations

from typing import Dict, Optional, Sequence

from retryctl.fallback import FallbackPolicy

_registry: Dict[str, FallbackPolicy] = {}


def get_or_create(
    name: str,
    command: Sequence[str],
    *,
    on_exit_codes: Sequence[int] = (),
    on_any_failure: bool = False,
) -> FallbackPolicy:
    """Return existing policy by *name* or create and register a new one."""
    if name not in _registry:
        _registry[name] = FallbackPolicy(
            command=list(command),
            on_exit_codes=list(on_exit_codes),
            on_any_failure=on_any_failure,
        )
    return _registry[name]


def get(name: str) -> Optional[FallbackPolicy]:
    """Return the policy registered under *name*, or None."""
    return _registry.get(name)


def register(name: str, policy: FallbackPolicy) -> None:
    """Explicitly register *policy* under *name*."""
    _registry[name] = policy


def remove(name: str) -> None:
    """Remove the policy registered under *name* (no-op if absent)."""
    _registry.pop(name, None)


def reset_all() -> None:
    """Clear all registered policies (useful in tests)."""
    _registry.clear()


def available() -> list[str]:
    """Return sorted list of registered policy names."""
    return sorted(_registry.keys())

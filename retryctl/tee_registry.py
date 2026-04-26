"""Global registry for named :class:`~retryctl.tee.TeeMiddleware` instances.

Allows different parts of the application to share a tee pipeline by name
without passing instances around explicitly.
"""
from __future__ import annotations

from typing import Dict, Optional

from retryctl.tee import Sink, TeeMiddleware

_registry: Dict[str, TeeMiddleware] = {}


def get_or_create(name: str, *, strict: bool = False) -> TeeMiddleware:
    """Return an existing :class:`TeeMiddleware` or create a new one."""
    if name not in _registry:
        _registry[name] = TeeMiddleware(strict=strict)
    return _registry[name]


def get(name: str) -> Optional[TeeMiddleware]:
    """Return a registered instance or *None*."""
    return _registry.get(name)


def register(name: str, tee: TeeMiddleware) -> None:
    """Explicitly register a pre-built :class:`TeeMiddleware` under *name*."""
    if not isinstance(tee, TeeMiddleware):
        raise TypeError(f"Expected TeeMiddleware, got {type(tee).__name__}")
    _registry[name] = tee


def add_sink(name: str, sink: Sink, *, strict: bool = False) -> TeeMiddleware:
    """Add *sink* to the named tee (creating it if necessary)."""
    tee = get_or_create(name, strict=strict)
    tee.add_sink(sink)
    return tee


def remove(name: str) -> None:
    """Remove a named entry (no-op if absent)."""
    _registry.pop(name, None)


def reset_all() -> None:
    """Clear the entire registry (useful in tests)."""
    _registry.clear()


def names() -> list[str]:
    """Return all registered names."""
    return list(_registry.keys())

"""Global registry for DrainController instances keyed by scope name.

Allows multiple parts of the application to share a single controller
for a given scope without passing it around explicitly.
"""
from __future__ import annotations

from typing import Dict, Optional

from retryctl.drain import DrainController

_registry: Dict[str, DrainController] = {}


def get_or_create(scope: str = "retryctl") -> DrainController:
    """Return the existing controller for *scope*, or create one."""
    if not scope:
        raise ValueError("scope must be a non-empty string")
    if scope not in _registry:
        _registry[scope] = DrainController()
    return _registry[scope]


def get(scope: str = "retryctl") -> Optional[DrainController]:
    """Return the controller for *scope*, or None if not registered."""
    return _registry.get(scope)


def register(scope: str, controller: DrainController) -> None:
    """Register an externally created *controller* under *scope*."""
    if not scope:
        raise ValueError("scope must be a non-empty string")
    if not isinstance(controller, DrainController):
        raise TypeError("controller must be a DrainController instance")
    _registry[scope] = controller


def remove(scope: str) -> None:
    """Remove the controller registered under *scope* (no-op if absent)."""
    _registry.pop(scope, None)


def drain_all() -> None:
    """Activate the drain flag on every registered controller."""
    for controller in list(_registry.values()):
        controller.start()


def reset_all() -> None:
    """Reset the drain flag on every registered controller (test helper)."""
    for controller in list(_registry.values()):
        controller.reset()
    _registry.clear()

"""Named registry for retry conditions so they can be referenced by string."""
from __future__ import annotations

from typing import Dict

from retryctl.condition import (
    RetryPredicate,
    all_of,
    any_of,
    never,
    on_any_failure,
    on_exit_codes,
)

_REGISTRY: Dict[str, RetryPredicate] = {}


def register(name: str, predicate: RetryPredicate) -> None:
    """Register *predicate* under *name*, overwriting any previous entry."""
    if not callable(predicate):
        raise TypeError(f"predicate must be callable, got {type(predicate)!r}")
    _REGISTRY[name] = predicate


def lookup(name: str) -> RetryPredicate:
    """Return the predicate registered under *name*.

    Raises
    ------
    KeyError
        If *name* has not been registered.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        available = ", ".join(sorted(_REGISTRY))
        raise KeyError(
            f"Unknown retry condition {name!r}. Available: {available}"
        ) from None


def available() -> list[str]:
    """Return a sorted list of all registered condition names."""
    return sorted(_REGISTRY)


def _bootstrap() -> None:
    """Populate the registry with built-in conditions."""
    register("any_failure", on_any_failure())
    register("never", never())
    # Common exit-code shortcuts
    register("on_exit_1", on_exit_codes(1))
    register("on_exit_1_2", on_exit_codes(1, 2))


_bootstrap()

"""Helpers to discover and load retryctl plugins from entry-points or paths."""
from __future__ import annotations

from typing import List

from retryctl.plugin import PluginError, PluginRegistry, get_default_registry


def load_plugins(module_paths: List[str], registry: PluginRegistry | None = None) -> List[str]:
    """Load a list of dotted module paths into *registry*.

    Returns the names of successfully loaded plugins.
    Raises :class:`PluginError` on the first failure.
    """
    reg = registry or get_default_registry()
    loaded: List[str] = []
    for path in module_paths:
        before = set(reg.available())
        reg.load_from_module(path)
        after = set(reg.available())
        new_names = after - before
        loaded.extend(sorted(new_names))
    return loaded


def build_middleware_from_plugins(
    names: List[str],
    registry: PluginRegistry | None = None,
    **kwargs,
) -> list:
    """Instantiate middleware objects for each plugin *name* in order.

    Extra *kwargs* are forwarded to every factory.
    """
    reg = registry or get_default_registry()
    middlewares = []
    for name in names:
        try:
            mw = reg.build(name, **kwargs)
        except PluginError:
            raise
        middlewares.append(mw)
    return middlewares


def describe_plugins(registry: PluginRegistry | None = None) -> List[dict]:
    """Return a list of dicts describing every registered plugin."""
    reg = registry or get_default_registry()
    result = []
    for name in reg.available():
        meta = reg.get(name)
        result.append(
            {
                "name": meta.name,
                "version": meta.version,
                "description": meta.description,
                "module_path": meta.module_path,
            }
        )
    return result

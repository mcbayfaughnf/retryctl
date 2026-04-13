"""Plugin system for retryctl middleware extensions."""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


class PluginError(Exception):
    """Raised when a plugin cannot be loaded or registered."""


@dataclass
class PluginMeta:
    """Metadata describing a registered plugin."""

    name: str
    module_path: str
    factory: Callable
    description: str = ""
    version: str = "0.1.0"


@dataclass
class PluginRegistry:
    """Central registry for retryctl plugins."""

    _plugins: Dict[str, PluginMeta] = field(default_factory=dict)

    def register(self, name: str, factory: Callable, *, description: str = "", version: str = "0.1.0", module_path: str = "") -> None:
        """Register a plugin factory under *name*."""
        if name in self._plugins:
            raise PluginError(f"Plugin '{name}' is already registered.")
        self._plugins[name] = PluginMeta(
            name=name,
            module_path=module_path,
            factory=factory,
            description=description,
            version=version,
        )

    def unregister(self, name: str) -> None:
        """Remove a plugin by name; silently ignored if absent."""
        self._plugins.pop(name, None)

    def get(self, name: str) -> PluginMeta:
        """Return plugin metadata or raise *PluginError*."""
        try:
            return self._plugins[name]
        except KeyError:
            raise PluginError(f"No plugin registered under '{name}'.")

    def build(self, name: str, **kwargs):
        """Instantiate the plugin identified by *name*."""
        meta = self.get(name)
        return meta.factory(**kwargs)

    def available(self) -> List[str]:
        """Return sorted list of registered plugin names."""
        return sorted(self._plugins)

    def load_from_module(self, module_path: str) -> None:
        """Import *module_path* and call its ``register_plugin(registry)`` hook."""
        try:
            mod = importlib.import_module(module_path)
        except ImportError as exc:
            raise PluginError(f"Cannot import plugin module '{module_path}': {exc}") from exc
        hook = getattr(mod, "register_plugin", None)
        if hook is None:
            raise PluginError(f"Module '{module_path}' has no 'register_plugin' function.")
        hook(self)


_default_registry: Optional[PluginRegistry] = None


def get_default_registry() -> PluginRegistry:
    global _default_registry
    if _default_registry is None:
        _default_registry = PluginRegistry()
    return _default_registry

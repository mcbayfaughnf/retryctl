"""Tests for retryctl.plugin."""
import pytest
import types

from retryctl.plugin import PluginError, PluginMeta, PluginRegistry


def _registry() -> PluginRegistry:
    return PluginRegistry()


class _DummyMiddleware:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, cmd, next_fn):
        return next_fn(cmd)


def _factory(**kwargs):
    return _DummyMiddleware(**kwargs)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class TestPluginRegistryRegister:
    def test_register_and_available(self):
        reg = _registry()
        reg.register("dummy", _factory)
        assert "dummy" in reg.available()

    def test_duplicate_raises(self):
        reg = _registry()
        reg.register("dummy", _factory)
        with pytest.raises(PluginError, match="already registered"):
            reg.register("dummy", _factory)

    def test_available_sorted(self):
        reg = _registry()
        reg.register("zebra", _factory)
        reg.register("alpha", _factory)
        assert reg.available() == ["alpha", "zebra"]

    def test_unregister_removes(self):
        reg = _registry()
        reg.register("dummy", _factory)
        reg.unregister("dummy")
        assert "dummy" not in reg.available()

    def test_unregister_missing_is_noop(self):
        reg = _registry()
        reg.unregister("nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

class TestPluginRegistryGet:
    def test_get_returns_meta(self):
        reg = _registry()
        reg.register("dummy", _factory, description="test", version="1.2.3")
        meta = reg.get("dummy")
        assert isinstance(meta, PluginMeta)
        assert meta.name == "dummy"
        assert meta.version == "1.2.3"
        assert meta.description == "test"

    def test_get_unknown_raises(self):
        reg = _registry()
        with pytest.raises(PluginError, match="No plugin"):
            reg.get("missing")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

class TestPluginRegistryBuild:
    def test_build_returns_instance(self):
        reg = _registry()
        reg.register("dummy", _factory)
        obj = reg.build("dummy", foo="bar")
        assert isinstance(obj, _DummyMiddleware)
        assert obj.kwargs == {"foo": "bar"}

    def test_build_unknown_raises(self):
        reg = _registry()
        with pytest.raises(PluginError):
            reg.build("missing")


# ---------------------------------------------------------------------------
# load_from_module
# ---------------------------------------------------------------------------

class TestLoadFromModule:
    def test_invalid_module_raises(self):
        reg = _registry()
        with pytest.raises(PluginError, match="module"):
            reg.load_from_module("retryctl._does_not_exist")

    def test_load_registers_plugins(self):
        """A module exposing RETRYCTL_PLUGINS dict should register all entries."""
        mod = types.ModuleType("_fake_plugin_module")
        mod.RETRYCTL_PLUGINS = {
            "fake": {"factory": _factory, "description": "fake plugin", "version": "0.1"},
        }
        reg = _registry()
        reg.load_from_module(mod)
        assert "fake" in reg.available()
        meta = reg.get("fake")
        assert meta.description == "fake plugin"
        assert meta.version == "0.1"

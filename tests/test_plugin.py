"""Tests for retryctl.plugin."""
import pytest

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
        with pytest.raises(PluginError, match="Cannot import"):
            reg.load_from_module("retryctl._no_such_module_xyz")

    def test_module_without_hook_raises(self, tmp_path, monkeypatch):
        import sys
        mod_path = tmp_path / "fake_plugin.py"
        mod_path.write_text("# no register_plugin here\n")
        monkeypatch.syspath_prepend(str(tmp_path))
        reg = _registry()
        with pytest.raises(PluginError, match="register_plugin"):
            reg.load_from_module("fake_plugin")
        sys.modules.pop("fake_plugin", None)

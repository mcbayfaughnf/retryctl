"""Tests for retryctl.plugin_loader."""
import sys
import textwrap

import pytest

from retryctl.plugin import PluginError, PluginRegistry
from retryctl.plugin_loader import build_middleware_from_plugins, describe_plugins, load_plugins


def _registry() -> PluginRegistry:
    return PluginRegistry()


def _write_plugin_module(tmp_path, name: str, plugin_name: str) -> None:
    """Write a minimal plugin module to *tmp_path*."""
    code = textwrap.dedent(f"""
        def register_plugin(registry):
            registry.register(
                "{plugin_name}",
                lambda **kw: kw,
                description="auto",
                version="0.0.1",
                module_path="{name}",
            )
    """)
    (tmp_path / f"{name}.py").write_text(code)


class TestLoadPlugins:
    def test_returns_plugin_names(self, tmp_path, monkeypatch):
        _write_plugin_module(tmp_path, "plug_a", "alpha")
        monkeypatch.syspath_prepend(str(tmp_path))
        reg = _registry()
        names = load_plugins(["plug_a"], registry=reg)
        assert names == ["alpha"]
        sys.modules.pop("plug_a", None)

    def test_multiple_modules(self, tmp_path, monkeypatch):
        _write_plugin_module(tmp_path, "plug_b", "beta")
        _write_plugin_module(tmp_path, "plug_c", "gamma")
        monkeypatch.syspath_prepend(str(tmp_path))
        reg = _registry()
        names = load_plugins(["plug_b", "plug_c"], registry=reg)
        assert set(names) == {"beta", "gamma"}
        sys.modules.pop("plug_b", None)
        sys.modules.pop("plug_c", None)

    def test_bad_module_raises(self):
        reg = _registry()
        with pytest.raises(PluginError):
            load_plugins(["retryctl._nonexistent_xyz"], registry=reg)


class TestBuildMiddlewareFromPlugins:
    def test_returns_instances(self):
        reg = _registry()
        reg.register("mw1", lambda **kw: {"id": 1, **kw})
        reg.register("mw2", lambda **kw: {"id": 2, **kw})
        result = build_middleware_from_plugins(["mw1", "mw2"], registry=reg)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

    def test_kwargs_forwarded(self):
        reg = _registry()
        reg.register("mw", lambda **kw: kw)
        result = build_middleware_from_plugins(["mw"], registry=reg, timeout=30)
        assert result[0]["timeout"] == 30

    def test_unknown_plugin_raises(self):
        reg = _registry()
        with pytest.raises(PluginError):
            build_middleware_from_plugins(["unknown"], registry=reg)


class TestDescribePlugins:
    def test_returns_list_of_dicts(self):
        reg = _registry()
        reg.register("plug", lambda **kw: kw, description="desc", version="1.0.0")
        info = describe_plugins(registry=reg)
        assert len(info) == 1
        assert info[0]["name"] == "plug"
        assert info[0]["version"] == "1.0.0"
        assert info[0]["description"] == "desc"

    def test_empty_registry(self):
        reg = _registry()
        assert describe_plugins(registry=reg) == []

"""Tests for retryctl.manifest and retryctl.manifest_middleware."""
from __future__ import annotations

import json
import pytest

from retryctl.manifest import Manifest, ManifestEntry
from retryctl.manifest_middleware import ManifestMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(code: int = 0) -> CommandResult:
    return CommandResult(command="echo hi", exit_code=code, stdout="", stderr="", attempts=1)


def _next(result: CommandResult):
    def _fn(*args, **kwargs):
        return result
    return _fn


# ---------------------------------------------------------------------------
# ManifestEntry
# ---------------------------------------------------------------------------

class TestManifestEntry:
    def test_to_dict_has_required_keys(self):
        e = ManifestEntry(name="cache", enabled=True, params={"ttl": 30})
        d = e.to_dict()
        assert d["name"] == "cache"
        assert d["enabled"] is True
        assert d["params"] == {"ttl": 30}

    def test_defaults(self):
        e = ManifestEntry(name="foo")
        assert e.enabled is True
        assert e.params == {}


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

class TestManifest:
    def test_add_and_get(self):
        m = Manifest()
        m.add(ManifestEntry(name="rate_limit"))
        assert m.get("rate_limit") is not None

    def test_get_missing_returns_none(self):
        m = Manifest()
        assert m.get("nope") is None

    def test_remove_existing(self):
        m = Manifest()
        m.add(ManifestEntry(name="x"))
        removed = m.remove("x")
        assert removed is True
        assert m.get("x") is None

    def test_remove_missing_returns_false(self):
        m = Manifest()
        assert m.remove("ghost") is False

    def test_enabled_names_filters_disabled(self):
        m = Manifest()
        m.add(ManifestEntry(name="a", enabled=True))
        m.add(ManifestEntry(name="b", enabled=False))
        assert m.enabled_names() == ["a"]

    def test_round_trip_json(self):
        m = Manifest()
        m.add(ManifestEntry(name="circuit_breaker", enabled=False, params={"threshold": 3}))
        restored = Manifest.from_json(m.to_json())
        entry = restored.get("circuit_breaker")
        assert entry is not None
        assert entry.enabled is False
        assert entry.params["threshold"] == 3

    def test_from_dict_missing_entries_defaults_to_empty(self):
        m = Manifest.from_dict({"version": "1"})
        assert m.entries == []


# ---------------------------------------------------------------------------
# ManifestMiddleware
# ---------------------------------------------------------------------------

class TestManifestMiddlewareEnabled:
    def test_calls_inner_when_enabled(self):
        called = []

        def inner(nxt, *a, **kw):
            called.append(True)
            return nxt(*a, **kw)

        m = Manifest()
        m.add(ManifestEntry(name="my_mw", enabled=True))
        mw = ManifestMiddleware("my_mw", m, inner)
        result = mw(_next(_result(0)))
        assert called == [True]

    def test_skips_inner_when_disabled(self):
        called = []

        def inner(nxt, *a, **kw):
            called.append(True)
            return nxt(*a, **kw)

        m = Manifest()
        m.add(ManifestEntry(name="my_mw", enabled=False))
        mw = ManifestMiddleware("my_mw", m, inner)
        result = mw(_next(_result(0)))
        assert called == []
        assert result.exit_code == 0

    def test_unknown_name_passes_through_by_default(self):
        called = []

        def inner(nxt, *a, **kw):
            called.append(True)
            return nxt(*a, **kw)

        m = Manifest()  # empty
        mw = ManifestMiddleware("unknown", m, inner)
        mw(_next(_result(0)))
        assert called == []

    def test_unknown_name_strict_raises(self):
        m = Manifest()
        mw = ManifestMiddleware("unknown", m, lambda nxt, *a, **kw: nxt(*a, **kw), strict=True)
        with pytest.raises(PermissionError, match="not registered"):
            mw(_next(_result(0)))

    def test_empty_name_raises(self):
        m = Manifest()
        with pytest.raises(ValueError):
            ManifestMiddleware("", m, lambda nxt, *a, **kw: nxt(*a, **kw))

"""Tests for retryctl.tag and retryctl.tag_middleware."""
from __future__ import annotations

import pytest

from retryctl.tag import TagError, TagSet
from retryctl.tag_middleware import TagMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> TagSet:
    return TagSet()


def _result(exit_code: int = 0) -> CommandResult:
    r = CommandResult.__new__(CommandResult)
    r.command = ["echo", "hi"]
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    r.attempts = 1
    r.elapsed = 0.0
    return r


def _next(result: CommandResult):
    def handler(cmd):
        return result
    return handler


# ---------------------------------------------------------------------------
# TagSet
# ---------------------------------------------------------------------------

class TestTagSetSet:
    def test_sets_valid_tag(self):
        ts = _ts()
        ts.set("env", "prod")
        assert ts.get("env") == "prod"

    def test_overwrites_existing(self):
        ts = _ts()
        ts.set("env", "dev")
        ts.set("env", "prod")
        assert ts.get("env") == "prod"

    def test_invalid_key_raises(self):
        ts = _ts()
        with pytest.raises(TagError):
            ts.set("bad key!", "v")

    def test_value_too_long_raises(self):
        ts = _ts()
        with pytest.raises(TagError):
            ts.set("k", "x" * 257)

    def test_value_exactly_max_is_ok(self):
        ts = _ts()
        ts.set("k", "x" * 256)  # should not raise


class TestTagSetRemove:
    def test_removes_existing(self):
        ts = _ts()
        ts.set("a", "1")
        ts.remove("a")
        assert "a" not in ts

    def test_missing_key_is_noop(self):
        ts = _ts()
        ts.remove("ghost")  # should not raise


class TestTagSetAll:
    def test_returns_copy(self):
        ts = _ts()
        ts.set("x", "1")
        d = ts.all()
        d["y"] = "2"
        assert "y" not in ts

    def test_len_reflects_tags(self):
        ts = _ts()
        assert len(ts) == 0
        ts.set("a", "1")
        assert len(ts) == 1


# ---------------------------------------------------------------------------
# TagMiddleware
# ---------------------------------------------------------------------------

class TestTagMiddlewareStatic:
    def test_attaches_static_tags(self):
        mw = TagMiddleware(tags={"service": "worker"})
        r = _result()
        out = mw(["echo"], _next(r))
        assert out.tags.get("service") == "worker"  # type: ignore[attr-defined]

    def test_no_tags_empty_tagset(self):
        mw = TagMiddleware()
        r = _result()
        out = mw(["echo"], _next(r))
        assert len(out.tags) == 0  # type: ignore[attr-defined]

    def test_static_tags_property(self):
        mw = TagMiddleware(tags={"k": "v"})
        assert mw.static_tags == {"k": "v"}


class TestTagMiddlewareResolver:
    def test_resolver_adds_dynamic_tag(self):
        def resolver(result):
            return {"exit": str(result.exit_code)}

        mw = TagMiddleware(resolver=resolver)
        r = _result(exit_code=42)
        out = mw(["false"], _next(r))
        assert out.tags.get("exit") == "42"  # type: ignore[attr-defined]

    def test_resolver_overrides_static(self):
        mw = TagMiddleware(
            tags={"status": "ok"},
            resolver=lambda _: {"status": "overridden"},
        )
        r = _result()
        out = mw(["echo"], _next(r))
        assert out.tags.get("status") == "overridden"  # type: ignore[attr-defined]

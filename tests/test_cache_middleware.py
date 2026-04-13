"""Tests for retryctl.cache_middleware."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from retryctl.cache import ResultCache
from retryctl.cache_middleware import CacheMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

CMD = ["echo", "hi"]


def _result(rc: int = 0, stdout: str = "ok", from_cache: bool = False) -> CommandResult:
    return CommandResult(
        command=CMD,
        returncode=rc,
        stdout=stdout,
        stderr="",
        attempts=1,
        from_cache=from_cache,
    )


def _next(rc: int = 0) -> MagicMock:
    handler = MagicMock(return_value=_result(rc=rc))
    return handler


# ---------------------------------------------------------------------------
# cache miss path
# ---------------------------------------------------------------------------

class TestCacheMiss:
    def test_delegates_to_next_on_miss(self):
        mw = CacheMiddleware(ttl=60.0)
        handler = _next(rc=0)
        mw(CMD, handler)
        handler.assert_called_once_with(CMD)

    def test_stores_successful_result(self):
        cache = ResultCache(default_ttl=60.0)
        mw = CacheMiddleware(cache=cache, ttl=60.0)
        mw(CMD, _next(rc=0))
        assert cache.get(CMD) is not None

    def test_does_not_store_failure_by_default(self):
        cache = ResultCache(default_ttl=60.0)
        mw = CacheMiddleware(cache=cache, ttl=60.0)
        mw(CMD, _next(rc=1))
        assert cache.get(CMD) is None

    def test_stores_failure_when_cache_failures_true(self):
        cache = ResultCache(default_ttl=60.0)
        mw = CacheMiddleware(cache=cache, ttl=60.0, cache_failures=True)
        mw(CMD, _next(rc=1))
        assert cache.get(CMD) is not None


# ---------------------------------------------------------------------------
# cache hit path
# ---------------------------------------------------------------------------

class TestCacheHit:
    def test_does_not_call_next_on_hit(self):
        cache = ResultCache(default_ttl=60.0)
        cache.set(CMD, stdout="cached", stderr="", returncode=0)
        mw = CacheMiddleware(cache=cache)
        handler = _next()
        mw(CMD, handler)
        handler.assert_not_called()

    def test_returns_from_cache_flag(self):
        cache = ResultCache(default_ttl=60.0)
        cache.set(CMD, stdout="cached", stderr="", returncode=0)
        mw = CacheMiddleware(cache=cache)
        result = mw(CMD, _next())
        assert result.from_cache is True

    def test_returns_cached_stdout(self):
        cache = ResultCache(default_ttl=60.0)
        cache.set(CMD, stdout="stored", stderr="", returncode=0)
        mw = CacheMiddleware(cache=cache)
        result = mw(CMD, _next())
        assert result.stdout == "stored"


# ---------------------------------------------------------------------------
# invalidate / clear
# ---------------------------------------------------------------------------

class TestInvalidate:
    def test_invalidate_removes_entry(self):
        cache = ResultCache(default_ttl=60.0)
        cache.set(CMD, stdout="x", stderr="", returncode=0)
        mw = CacheMiddleware(cache=cache)
        assert mw.invalidate(CMD) is True
        assert cache.get(CMD) is None

    def test_clear_empties_cache(self):
        cache = ResultCache(default_ttl=60.0)
        cache.set(CMD, stdout="x", stderr="", returncode=0)
        mw = CacheMiddleware(cache=cache)
        mw.clear()
        assert cache.get(CMD) is None

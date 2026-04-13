"""Tests for retryctl.cache."""

from __future__ import annotations

import time
import pytest

from retryctl.cache import CacheEntry, ResultCache


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

CMD = ["echo", "hello"]


def _cache(ttl: float = 60.0) -> ResultCache:
    return ResultCache(default_ttl=ttl)


# ---------------------------------------------------------------------------
# CacheEntry
# ---------------------------------------------------------------------------

class TestCacheEntry:
    def test_not_expired_immediately(self):
        e = CacheEntry(stdout="ok", stderr="", returncode=0, ttl=60.0)
        assert not e.expired

    def test_expired_after_ttl(self):
        e = CacheEntry(stdout="ok", stderr="", returncode=0,
                       created_at=time.monotonic() - 61.0, ttl=60.0)
        assert e.expired


# ---------------------------------------------------------------------------
# ResultCache init
# ---------------------------------------------------------------------------

class TestResultCacheInit:
    def test_negative_ttl_raises(self):
        with pytest.raises(ValueError):
            ResultCache(default_ttl=-1.0)

    def test_zero_ttl_raises(self):
        with pytest.raises(ValueError):
            ResultCache(default_ttl=0.0)


# ---------------------------------------------------------------------------
# key
# ---------------------------------------------------------------------------

class TestResultCacheKey:
    def test_same_command_same_key(self):
        c = _cache()
        assert c.key(CMD) == c.key(CMD)

    def test_different_command_different_key(self):
        c = _cache()
        assert c.key(["echo", "hello"]) != c.key(["echo", "world"])

    def test_key_is_hex_string(self):
        c = _cache()
        k = c.key(CMD)
        int(k, 16)  # must not raise


# ---------------------------------------------------------------------------
# get / set
# ---------------------------------------------------------------------------

class TestResultCacheGetSet:
    def test_miss_returns_none(self):
        assert _cache().get(CMD) is None

    def test_hit_returns_entry(self):
        c = _cache()
        c.set(CMD, stdout="hi", stderr="", returncode=0)
        assert c.get(CMD) is not None

    def test_stored_fields(self):
        c = _cache()
        c.set(CMD, stdout="out", stderr="err", returncode=42)
        e = c.get(CMD)
        assert e.stdout == "out"
        assert e.stderr == "err"
        assert e.returncode == 42

    def test_expired_entry_returns_none(self):
        c = _cache(ttl=0.001)
        c.set(CMD, stdout="x", stderr="", returncode=0)
        time.sleep(0.05)
        assert c.get(CMD) is None

    def test_custom_ttl_overrides_default(self):
        c = _cache(ttl=60.0)
        c.set(CMD, stdout="x", stderr="", returncode=0, ttl=0.001)
        time.sleep(0.05)
        assert c.get(CMD) is None


# ---------------------------------------------------------------------------
# invalidate / clear
# ---------------------------------------------------------------------------

class TestResultCacheInvalidate:
    def test_invalidate_existing_returns_true(self):
        c = _cache()
        c.set(CMD, stdout="", stderr="", returncode=0)
        assert c.invalidate(CMD) is True

    def test_invalidate_missing_returns_false(self):
        assert _cache().invalidate(CMD) is False

    def test_clear_empties_store(self):
        c = _cache()
        c.set(CMD, stdout="", stderr="", returncode=0)
        c.clear()
        assert len(c) == 0

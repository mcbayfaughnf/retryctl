"""Tests for retryctl.bulkhead and retryctl.bulkhead_middleware."""
from __future__ import annotations

import pytest

from retryctl.bulkhead import (
    BulkheadFull,
    BulkheadPartition,
    get_or_create,
    get,
    remove,
    reset_all,
)
from retryctl.bulkhead_middleware import BulkheadMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _result(code: int = 0) -> CommandResult:
    return CommandResult(command="echo hi", exit_code=code, stdout="", stderr="", attempts=1)


def _next(result: CommandResult = None):
    r = result or _result()
    def fn():
        return r
    return fn


@pytest.fixture(autouse=True)
def _clean():
    reset_all()
    yield
    reset_all()


# ---------------------------------------------------------------------------
# BulkheadPartition
# ---------------------------------------------------------------------------

class TestBulkheadPartitionInit:
    def test_zero_limit_raises(self):
        with pytest.raises(ValueError):
            BulkheadPartition(name="x", limit=0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError):
            BulkheadPartition(name="x", limit=-1)

    def test_valid_partition(self):
        p = BulkheadPartition(name="x", limit=3)
        assert p.limit == 3
        assert p.active == 0
        assert p.available == 3


class TestBulkheadPartitionAcquireRelease:
    def test_acquire_decrements_available(self):
        p = BulkheadPartition(name="x", limit=2)
        p.acquire()
        assert p.active == 1
        assert p.available == 1

    def test_release_increments_available(self):
        p = BulkheadPartition(name="x", limit=2)
        p.acquire()
        p.release()
        assert p.active == 0
        assert p.available == 2

    def test_full_partition_raises(self):
        p = BulkheadPartition(name="x", limit=1)
        p.acquire()
        with pytest.raises(BulkheadFull) as exc_info:
            p.acquire()
        assert exc_info.value.name == "x"
        assert exc_info.value.limit == 1

    def test_release_after_full_allows_acquire(self):
        p = BulkheadPartition(name="x", limit=1)
        p.acquire()
        p.release()
        p.acquire()  # should not raise


# ---------------------------------------------------------------------------
# registry helpers
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_get_or_create_returns_same_instance(self):
        a = get_or_create("svc", limit=5)
        b = get_or_create("svc", limit=5)
        assert a is b

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError):
            get("missing")

    def test_remove_clears_partition(self):
        get_or_create("svc", limit=2)
        remove("svc")
        with pytest.raises(KeyError):
            get("svc")


# ---------------------------------------------------------------------------
# BulkheadMiddleware
# ---------------------------------------------------------------------------

class TestBulkheadMiddleware:
    def test_delegates_to_next(self):
        mw = BulkheadMiddleware(name="t", limit=2)
        result = mw(_next())
        assert result.exit_code == 0

    def test_releases_slot_after_call(self):
        mw = BulkheadMiddleware(name="t", limit=1)
        mw(_next())
        assert mw.active == 0
        assert mw.available == 1

    def test_raises_when_full(self):
        part = BulkheadPartition(name="t", limit=1)
        part.acquire()  # fill it
        mw = BulkheadMiddleware(partition=part)
        with pytest.raises(BulkheadFull):
            mw(_next())

    def test_releases_slot_on_exception(self):
        mw = BulkheadMiddleware(name="t", limit=2)
        def boom():
            raise RuntimeError("oops")
        with pytest.raises(RuntimeError):
            mw(boom)
        assert mw.active == 0

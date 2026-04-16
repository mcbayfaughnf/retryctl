"""Tests for ConcurrencySemaphore and ConcurrencyMiddleware."""
from __future__ import annotations

import threading
import pytest

from retryctl.concurrency import ConcurrencySemaphore, ConcurrencyExceeded
from retryctl.concurrency_middleware import ConcurrencyMiddleware
from retryctl.runner import CommandResult


def _result(code: int = 0) -> CommandResult:
    return CommandResult(command="echo hi", exit_code=code, stdout="", stderr="", attempts=1)


# ---------------------------------------------------------------------------
# ConcurrencySemaphore
# ---------------------------------------------------------------------------

class TestConcurrencySemaphoreInit:
    def test_invalid_limit_raises(self):
        with pytest.raises(ValueError):
            ConcurrencySemaphore(limit=0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError):
            ConcurrencySemaphore(limit=-1)

    def test_valid_limit(self):
        s = ConcurrencySemaphore(limit=3)
        assert s.limit == 3


class TestConcurrencySemaphoreAcquireRelease:
    def test_active_increments_on_acquire(self):
        s = ConcurrencySemaphore(limit=2)
        s.acquire()
        assert s.active == 1

    def test_active_decrements_on_release(self):
        s = ConcurrencySemaphore(limit=2)
        s.acquire()
        s.release()
        assert s.active == 0

    def test_exceeds_limit_raises(self):
        s = ConcurrencySemaphore(limit=1)
        s.acquire()
        with pytest.raises(ConcurrencyExceeded) as exc_info:
            s.acquire()
        assert exc_info.value.limit == 1

    def test_available_decreases(self):
        s = ConcurrencySemaphore(limit=3)
        s.acquire()
        s.acquire()
        assert s.available == 1

    def test_slot_freed_after_release(self):
        s = ConcurrencySemaphore(limit=1)
        s.acquire()
        s.release()
        s.acquire()  # should not raise
        assert s.active == 1


# ---------------------------------------------------------------------------
# ConcurrencyMiddleware
# ---------------------------------------------------------------------------

class TestConcurrencyMiddlewareSuccess:
    def test_delegates_to_next(self):
        mw = ConcurrencyMiddleware(limit=2)
        result = mw(lambda: _result(0))
        assert result.exit_code == 0

    def test_active_is_zero_after_call(self):
        mw = ConcurrencyMiddleware(limit=2)
        mw(lambda: _result(0))
        assert mw.active == 0

    def test_raises_when_limit_reached(self):
        mw = ConcurrencyMiddleware(limit=1)
        barrier = threading.Barrier(2)
        errors: list[Exception] = []

        def slow_next():
            barrier.wait()  # sync both threads inside acquire
            return _result(0)

        def run():
            try:
                mw(slow_next)
            except ConcurrencyExceeded as e:
                errors.append(e)

        # Manually fill the slot then try again
        mw._sem.acquire()
        with pytest.raises(ConcurrencyExceeded):
            mw(lambda: _result(0))
        mw._sem.release()

    def test_limit_property(self):
        mw = ConcurrencyMiddleware(limit=5)
        assert mw.limit == 5

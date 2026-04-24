"""Tests for retryctl.backpressure_middleware."""
from __future__ import annotations

import pytest

from retryctl.backpressure import (
    BackpressureActive,
    BackpressurePolicy,
    BackpressureTracker,
)
from retryctl.backpressure_middleware import BackpressureMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0) -> CommandResult:
    r = CommandResult.__new__(CommandResult)
    r.command = ["echo", "hi"]
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    r.attempts = 1
    r.elapsed = 0.01
    return r


def _next(exit_code: int = 0):
    def fn() -> CommandResult:
        return _result(exit_code)
    return fn


def _middleware(
    threshold: float = 0.8,
    window: int = 5,
) -> BackpressureMiddleware:
    policy = BackpressurePolicy(threshold=threshold, window=window)
    return BackpressureMiddleware(policy=policy)


# ---------------------------------------------------------------------------
# success path
# ---------------------------------------------------------------------------

class TestBackpressureMiddlewareSuccess:
    def test_delegates_to_next_when_load_is_low(self):
        mw = _middleware(threshold=0.8)
        result = mw(_next(0), load=0.3)
        assert result.exit_code == 0

    def test_no_load_sample_passes_through(self):
        mw = _middleware(threshold=0.8)
        result = mw(_next(0))
        assert result.exit_code == 0

    def test_records_load_sample(self):
        mw = _middleware(threshold=0.8)
        mw(_next(0), load=0.5)
        assert mw.tracker.current_load == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# backpressure active
# ---------------------------------------------------------------------------

class TestBackpressureMiddlewareActive:
    def test_raises_when_load_exceeds_threshold(self):
        mw = _middleware(threshold=0.8)
        with pytest.raises(BackpressureActive):
            mw(_next(0), load=0.9)

    def test_next_not_called_when_active(self):
        called = []

        def guarded_next() -> CommandResult:
            called.append(True)
            return _result(0)

        mw = _middleware(threshold=0.8)
        with pytest.raises(BackpressureActive):
            mw(guarded_next, load=0.95)

        assert not called

    def test_pre_loaded_tracker_triggers_without_new_sample(self):
        policy = BackpressurePolicy(threshold=0.8, window=3)
        tracker = BackpressureTracker(policy=policy)
        tracker.record(0.9)
        mw = BackpressureMiddleware(tracker=tracker)
        with pytest.raises(BackpressureActive):
            mw(_next(0))


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestBackpressureMiddlewareReset:
    def test_reset_clears_load(self):
        mw = _middleware(threshold=0.8)
        # saturate the tracker
        try:
            mw(_next(0), load=0.95)
        except BackpressureActive:
            pass
        mw.reset()
        # should pass now
        result = mw(_next(0), load=0.1)
        assert result.exit_code == 0

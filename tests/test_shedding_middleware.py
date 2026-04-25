"""Tests for retryctl.shedding_middleware."""
from __future__ import annotations

import pytest

from retryctl.runner import CommandResult
from retryctl.shedding import LoadShedded, SheddingPolicy
from retryctl.shedding_middleware import SheddingMiddleware


def _result(exit_code: int = 0) -> CommandResult:
    return CommandResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        elapsed=0.1,
    )


def _next(exit_code: int = 0):
    def _fn():
        return _result(exit_code)
    return _fn


def _middleware(threshold: float = 0.8) -> SheddingMiddleware:
    return SheddingMiddleware(policy=SheddingPolicy(threshold=threshold, window=60.0))


class TestSheddingMiddlewareSuccess:
    def test_delegates_to_next_on_low_load(self):
        mw = _middleware(threshold=0.8)
        result = mw(_next(0))
        assert result.exit_code == 0

    def test_records_success_on_zero_exit(self):
        mw = _middleware(threshold=0.8)
        mw(_next(0))
        assert mw.tracker.current_load() == 0.0

    def test_records_failure_on_nonzero_exit(self):
        mw = _middleware(threshold=0.8)
        mw(_next(1))
        assert mw.tracker.current_load() == 1.0


class TestSheddingMiddlewareShed:
    def test_raises_load_shedded_above_threshold(self):
        policy = SheddingPolicy(threshold=0.5, load_fn=lambda: 0.9)
        mw = SheddingMiddleware(policy=policy)
        with pytest.raises(LoadShedded):
            mw(_next(0))

    def test_exception_carries_load_and_threshold(self):
        policy = SheddingPolicy(threshold=0.5, load_fn=lambda: 0.75)
        mw = SheddingMiddleware(policy=policy)
        with pytest.raises(LoadShedded) as exc_info:
            mw(_next(0))
        assert exc_info.value.load == pytest.approx(0.75)
        assert exc_info.value.threshold == pytest.approx(0.5)


class TestSheddingMiddlewareReset:
    def test_reset_clears_tracker(self):
        mw = _middleware(threshold=0.8)
        mw(_next(1))
        mw.reset()
        assert mw.tracker.current_load() == 0.0

    def test_tracker_property_returns_tracker(self):
        mw = _middleware()
        from retryctl.shedding import SheddingTracker
        assert isinstance(mw.tracker, SheddingTracker)

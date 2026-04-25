"""Tests for retryctl.fence and retryctl.fence_middleware."""
from __future__ import annotations

import pytest

from retryctl.fence import FenceBlocked, FencePolicy, FenceTracker
from retryctl.fence_middleware import FenceMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    return CommandResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        elapsed=0.0,
    )


# ---------------------------------------------------------------------------
# FencePolicy
# ---------------------------------------------------------------------------

class TestFencePolicyInit:
    def test_valid_policy(self):
        p = FencePolicy(min_successes=2, max_failures=5, window=30.0)
        assert p.min_successes == 2
        assert p.max_failures == 5
        assert p.window == 30.0

    def test_zero_min_successes_raises(self):
        with pytest.raises(ValueError, match="min_successes"):
            FencePolicy(min_successes=0)

    def test_zero_max_failures_raises(self):
        with pytest.raises(ValueError, match="max_failures"):
            FencePolicy(max_failures=0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            FencePolicy(window=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            FencePolicy(window=-1.0)


# ---------------------------------------------------------------------------
# FenceTracker
# ---------------------------------------------------------------------------

@pytest.fixture()
def _tracker() -> FenceTracker:
    return FenceTracker(policy=FencePolicy(min_successes=1, max_failures=2, window=60.0))


class TestFenceTrackerCounts:
    def test_initial_counts_are_zero(self, _tracker):
        assert _tracker.successes == 0
        assert _tracker.failures == 0

    def test_record_success_increments(self, _tracker):
        _tracker.record_success()
        assert _tracker.successes == 1

    def test_record_failure_increments(self, _tracker):
        _tracker.record_failure()
        assert _tracker.failures == 1

    def test_reset_clears_all(self, _tracker):
        _tracker.record_success()
        _tracker.record_failure()
        _tracker.reset()
        assert _tracker.successes == 0
        assert _tracker.failures == 0


class TestFenceTrackerCheck:
    def test_check_passes_when_below_threshold(self, _tracker):
        _tracker.record_failure()
        _tracker.check()  # 1 failure < max_failures=2, should not raise

    def test_check_raises_when_failures_exceed_and_no_successes(self, _tracker):
        _tracker.record_failure()
        _tracker.record_failure()
        with pytest.raises(FenceBlocked) as exc_info:
            _tracker.check()
        assert exc_info.value.failures == 2
        assert exc_info.value.successes == 0

    def test_check_passes_after_success_despite_failures(self, _tracker):
        _tracker.record_failure()
        _tracker.record_failure()
        _tracker.record_success()
        _tracker.check()  # successes >= min_successes, should not raise


# ---------------------------------------------------------------------------
# FenceMiddleware
# ---------------------------------------------------------------------------

@pytest.fixture()
def _middleware() -> FenceMiddleware:
    policy = FencePolicy(min_successes=1, max_failures=2, window=60.0)
    return FenceMiddleware(policy=policy)


class TestFenceMiddlewareSuccess:
    def test_delegates_to_next(self, _middleware):
        called = []
        def next_fn():
            called.append(True)
            return _result(0)
        _middleware(next_fn)
        assert called

    def test_records_success_on_zero_exit(self, _middleware):
        _middleware(lambda: _result(0))
        assert _middleware.tracker.successes == 1

    def test_records_failure_on_nonzero_exit(self, _middleware):
        _middleware(lambda: _result(1))
        assert _middleware.tracker.failures == 1

    def test_blocks_after_max_failures(self, _middleware):
        _middleware(lambda: _result(1))
        _middleware(lambda: _result(1))
        with pytest.raises(FenceBlocked):
            _middleware(lambda: _result(0))

    def test_reset_clears_state(self, _middleware):
        _middleware(lambda: _result(1))
        _middleware(lambda: _result(1))
        _middleware.reset()
        result = _middleware(lambda: _result(0))  # should not raise
        assert result.exit_code == 0

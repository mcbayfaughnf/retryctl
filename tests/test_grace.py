"""Tests for retryctl.grace and retryctl.grace_middleware."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from retryctl.grace import GraceMiddleware, GracePolicy, GracePeriodActive, GraceTracker
from retryctl.grace_middleware import GraceMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    r.stdout = b""
    r.stderr = b""
    return r


def _next(result: CommandResult):
    def _fn(*args, **kwargs):
        return result
    return _fn


# ---------------------------------------------------------------------------
# GracePolicy
# ---------------------------------------------------------------------------

class TestGracePolicyInit:
    def test_valid_policy(self):
        p = GracePolicy(window=5.0)
        assert p.window == 5.0

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            GracePolicy(window=0.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            GracePolicy(window=-1.0)

    def test_suppress_defaults_to_true(self):
        p = GracePolicy(window=1.0)
        assert p.suppress_on_failure is True


# ---------------------------------------------------------------------------
# GraceTracker
# ---------------------------------------------------------------------------

class TestGraceTracker:
    def test_in_grace_period_immediately(self):
        tracker = GraceTracker(GracePolicy(window=60.0))
        assert tracker.in_grace_period() is True

    def test_not_in_grace_period_after_window(self):
        tracker = GraceTracker(GracePolicy(window=0.01))
        time.sleep(0.02)
        assert tracker.in_grace_period() is False

    def test_remaining_decreases(self):
        tracker = GraceTracker(GracePolicy(window=60.0))
        r1 = tracker.remaining()
        time.sleep(0.01)
        r2 = tracker.remaining()
        assert r2 < r1

    def test_check_success_does_not_raise(self):
        tracker = GraceTracker(GracePolicy(window=60.0))
        tracker.check(_result(0))  # should not raise

    def test_check_failure_in_window_raises(self):
        tracker = GraceTracker(GracePolicy(window=60.0))
        with pytest.raises(GracePeriodActive):
            tracker.check(_result(1))

    def test_check_failure_outside_window_does_not_raise(self):
        tracker = GraceTracker(GracePolicy(window=0.01))
        time.sleep(0.02)
        tracker.check(_result(1))  # should not raise

    def test_reset_restarts_window(self):
        tracker = GraceTracker(GracePolicy(window=0.01))
        time.sleep(0.02)
        assert tracker.in_grace_period() is False
        tracker.reset()
        assert tracker.in_grace_period() is True


# ---------------------------------------------------------------------------
# GraceMiddleware
# ---------------------------------------------------------------------------

class TestGraceMiddlewareSuccess:
    def test_delegates_to_next(self):
        mw = GraceMiddleware(GracePolicy(window=60.0))
        result = _result(0)
        assert mw(_next(result)) is result

    def test_raises_on_failure_in_window(self):
        mw = GraceMiddleware(GracePolicy(window=60.0))
        with pytest.raises(GracePeriodActive):
            mw(_next(_result(1)))

    def test_in_grace_period_true_initially(self):
        mw = GraceMiddleware(GracePolicy(window=60.0))
        assert mw.in_grace_period() is True

    def test_remaining_positive(self):
        mw = GraceMiddleware(GracePolicy(window=60.0))
        assert mw.remaining() > 0

    def test_reset_restarts(self):
        mw = GraceMiddleware(GracePolicy(window=0.01))
        time.sleep(0.02)
        assert mw.in_grace_period() is False
        mw.reset()
        assert mw.in_grace_period() is True

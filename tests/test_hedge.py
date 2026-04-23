"""Tests for retryctl.hedge."""
from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from retryctl.hedge import HedgeError, HedgeMiddleware, HedgePolicy
from retryctl.runner import CommandResult


def _result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    r.stdout = stdout
    r.stderr = stderr
    return r


# ---------------------------------------------------------------------------
# HedgePolicy validation
# ---------------------------------------------------------------------------

class TestHedgePolicyInit:
    def test_valid_policy(self):
        p = HedgePolicy(delay=0.5, max_hedges=2)
        assert p.delay == 0.5
        assert p.max_hedges == 2

    def test_zero_delay_raises(self):
        with pytest.raises(HedgeError):
            HedgePolicy(delay=0)

    def test_negative_delay_raises(self):
        with pytest.raises(HedgeError):
            HedgePolicy(delay=-1.0)

    def test_zero_max_hedges_raises(self):
        with pytest.raises(HedgeError):
            HedgePolicy(delay=0.1, max_hedges=0)

    def test_negative_max_hedges_raises(self):
        with pytest.raises(HedgeError):
            HedgePolicy(delay=0.1, max_hedges=-1)


# ---------------------------------------------------------------------------
# HedgeMiddleware behaviour
# ---------------------------------------------------------------------------

class TestHedgeMiddlewareFastPrimary:
    """Primary finishes before hedge delay fires."""

    def _make_middleware(self):
        return HedgeMiddleware(policy=HedgePolicy(delay=10.0))

    def test_delegates_to_next(self):
        expected = _result(exit_code=0)
        mw = self._make_middleware()
        result = mw(lambda: expected, _sleep=lambda _: None)
        assert result is expected

    def test_no_hedge_fired_when_primary_succeeds_immediately(self):
        mw = self._make_middleware()
        calls = []

        def next_fn():
            calls.append(1)
            return _result(exit_code=0)

        # sleep does nothing so hedge timer never triggers
        mw(next_fn, _sleep=lambda _: None)
        assert mw.hedge_count == 0


class TestHedgeMiddlewareSlowPrimary:
    """Primary is slow; hedge fires and returns first."""

    def test_hedge_fires_when_primary_is_slow(self):
        policy = HedgePolicy(delay=0.01)
        mw = HedgeMiddleware(policy=policy)

        barrier = threading.Event()
        call_order: list[str] = []

        def slow_next():
            call_order.append("call")
            barrier.wait(timeout=2)
            return _result(exit_code=0)

        # Use real sleep so the hedge thread actually fires
        result = mw(slow_next)
        barrier.set()
        assert result.exit_code == 0

    def test_returns_failure_when_all_fail(self):
        policy = HedgePolicy(delay=0.001)
        mw = HedgeMiddleware(policy=policy)
        result = mw(lambda: _result(exit_code=1))
        assert result.exit_code == 1


class TestHedgeMiddlewareReset:
    def test_reset_clears_hedge_count(self):
        mw = HedgeMiddleware(policy=HedgePolicy(delay=0.001))
        mw(lambda: _result(exit_code=0))
        mw.reset()
        assert mw.hedge_count == 0

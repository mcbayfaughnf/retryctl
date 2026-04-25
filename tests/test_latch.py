"""Tests for retryctl.latch."""
from __future__ import annotations

import pytest

from retryctl.latch import (
    LatchAlreadyTripped,
    LatchMiddleware,
    LatchPolicy,
    LatchState,
)
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0, attempts: int = 1) -> CommandResult:
    return CommandResult(
        command="echo hi",
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=attempts,
        elapsed=0.0,
    )


def _next(result: CommandResult):
    """Return a callable that always returns *result*."""
    def _fn(_command: str) -> CommandResult:
        return result
    return _fn


# ---------------------------------------------------------------------------
# LatchPolicy
# ---------------------------------------------------------------------------

class TestLatchPolicyInit:
    def test_default_success_codes(self):
        p = LatchPolicy()
        assert p.success_codes == (0,)

    def test_empty_success_codes_raises(self):
        with pytest.raises(ValueError, match="success_codes"):
            LatchPolicy(success_codes=())

    def test_custom_success_codes(self):
        p = LatchPolicy(success_codes=(0, 2))
        assert 2 in p.success_codes

    def test_is_success_true(self):
        p = LatchPolicy()
        assert p.is_success(_result(0)) is True

    def test_is_success_false(self):
        p = LatchPolicy()
        assert p.is_success(_result(1)) is False


# ---------------------------------------------------------------------------
# LatchState
# ---------------------------------------------------------------------------

class TestLatchState:
    def test_not_tripped_initially(self):
        s = LatchState()
        assert s.tripped is False

    def test_winning_result_none_initially(self):
        s = LatchState()
        assert s.winning_result is None

    def test_trip_sets_tripped(self):
        s = LatchState()
        s.trip(_result())
        assert s.tripped is True

    def test_trip_stores_result(self):
        s = LatchState()
        r = _result(exit_code=0, attempts=3)
        s.trip(r)
        assert s.winning_result is r

    def test_reset_clears_state(self):
        s = LatchState()
        s.trip(_result())
        s.reset()
        assert s.tripped is False
        assert s.winning_result is None


# ---------------------------------------------------------------------------
# LatchMiddleware – success path
# ---------------------------------------------------------------------------

class TestLatchMiddlewareSuccess:
    def test_delegates_to_next_on_first_call(self):
        r = _result(0)
        mw = LatchMiddleware()
        result = mw(_next(r), "echo hi")
        assert result is r

    def test_trips_after_success(self):
        mw = LatchMiddleware()
        mw(_next(_result(0)), "echo hi")
        assert mw.state.tripped is True

    def test_second_call_returns_cached_result(self):
        r = _result(0)
        mw = LatchMiddleware()
        mw(_next(r), "echo hi")
        result2 = mw(_next(_result(1)), "echo hi")
        assert result2 is r

    def test_does_not_trip_on_failure(self):
        mw = LatchMiddleware()
        mw(_next(_result(1)), "echo hi")
        assert mw.state.tripped is False


# ---------------------------------------------------------------------------
# LatchMiddleware – raise_on_tripped
# ---------------------------------------------------------------------------

class TestLatchMiddlewareRaiseOnTripped:
    def test_raises_latch_already_tripped(self):
        r = _result(0)
        mw = LatchMiddleware(policy=LatchPolicy(raise_on_tripped=True))
        mw(_next(r), "echo hi")
        with pytest.raises(LatchAlreadyTripped) as exc_info:
            mw(_next(_result(1)), "echo hi")
        assert exc_info.value.result is r

    def test_exception_message_contains_exit_code(self):
        mw = LatchMiddleware(policy=LatchPolicy(raise_on_tripped=True))
        mw(_next(_result(0)), "echo hi")
        with pytest.raises(LatchAlreadyTripped, match="exit_code=0"):
            mw(_next(_result(1)), "echo hi")


# ---------------------------------------------------------------------------
# LatchMiddleware – reset
# ---------------------------------------------------------------------------

class TestLatchMiddlewareReset:
    def test_reset_allows_new_trip(self):
        r1 = _result(0, attempts=1)
        r2 = _result(0, attempts=2)
        mw = LatchMiddleware()
        mw(_next(r1), "echo hi")
        mw.reset()
        mw(_next(r2), "echo hi")
        assert mw.state.winning_result is r2

    def test_reset_exposes_state(self):
        mw = LatchMiddleware()
        assert isinstance(mw.state, LatchState)

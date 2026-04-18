"""Tests for retryctl.cooldown_middleware."""
from __future__ import annotations

import pytest

from retryctl.cooldown import CooldownActive, CooldownPolicy
from retryctl.cooldown_middleware import CooldownMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = object.__new__(CommandResult)
    r.__dict__.update(
        command=["echo", "hi"],
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        duration=0.1,
    )
    return r


def _next(result: CommandResult):
    def fn(cmd):
        return result
    return fn


class TestCooldownMiddlewareSuccess:
    def test_delegates_to_next_on_first_call(self):
        mw = CooldownMiddleware(CooldownPolicy(period=5.0, command="c"))
        expected = _result(0)
        result = mw(["echo"], _next(expected))
        assert result is expected

    def test_records_attempt_after_call(self):
        mw = CooldownMiddleware(CooldownPolicy(period=5.0, command="c"))
        mw(["echo"], _next(_result()))
        assert mw.tracker.last_attempt is not None

    def test_second_call_raises_cooldown(self):
        mw = CooldownMiddleware(CooldownPolicy(period=60.0, command="c"))
        mw(["echo"], _next(_result()))
        with pytest.raises(CooldownActive):
            mw(["echo"], _next(_result()))

    def test_reset_allows_second_call(self):
        mw = CooldownMiddleware(CooldownPolicy(period=60.0, command="c"))
        mw(["echo"], _next(_result()))
        mw.reset()
        result = mw(["echo"], _next(_result(0)))
        assert result.exit_code == 0

    def test_tracker_property_returns_tracker(self):
        policy = CooldownPolicy(period=1.0)
        mw = CooldownMiddleware(policy)
        from retryctl.cooldown import CooldownTracker
        assert isinstance(mw.tracker, CooldownTracker)

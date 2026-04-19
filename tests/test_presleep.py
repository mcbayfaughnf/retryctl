"""Tests for retryctl.presleep."""
from __future__ import annotations

import pytest

from retryctl.presleep import PreSleepConfig, PreSleepMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = CommandResult.__new__(CommandResult)
    r.command = ["echo", "hi"]
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    r.attempts = 1
    r.elapsed = 0.0
    return r


def _next(exit_code: int = 0):
    def fn():
        return _result(exit_code)
    return fn


# ---------------------------------------------------------------------------
# PreSleepConfig
# ---------------------------------------------------------------------------

class TestPreSleepConfig:
    def test_valid_config(self):
        cfg = PreSleepConfig(delay=1.5)
        assert cfg.delay == 1.5
        assert cfg.skip_first is True

    def test_zero_delay_is_valid(self):
        cfg = PreSleepConfig(delay=0)
        assert cfg.delay == 0

    def test_negative_delay_raises(self):
        with pytest.raises(ValueError, match="delay"):
            PreSleepConfig(delay=-0.1)

    def test_skip_first_false(self):
        cfg = PreSleepConfig(delay=1.0, skip_first=False)
        assert cfg.skip_first is False


# ---------------------------------------------------------------------------
# PreSleepMiddleware
# ---------------------------------------------------------------------------

class TestPreSleepMiddlewareSkipFirst:
    def test_no_sleep_on_first_attempt(self):
        slept: list[float] = []
        cfg = PreSleepConfig(delay=2.0, skip_first=True)
        mw = PreSleepMiddleware(cfg, sleep_fn=slept.append)
        mw(_next())
        assert slept == []

    def test_sleeps_on_second_attempt(self):
        slept: list[float] = []
        cfg = PreSleepConfig(delay=2.0, skip_first=True)
        mw = PreSleepMiddleware(cfg, sleep_fn=slept.append)
        mw(_next())
        mw(_next())
        assert slept == [2.0]

    def test_sleeps_every_attempt_when_skip_first_false(self):
        slept: list[float] = []
        cfg = PreSleepConfig(delay=1.0, skip_first=False)
        mw = PreSleepMiddleware(cfg, sleep_fn=slept.append)
        mw(_next())
        mw(_next())
        assert slept == [1.0, 1.0]

    def test_zero_delay_never_sleeps(self):
        slept: list[float] = []
        cfg = PreSleepConfig(delay=0, skip_first=False)
        mw = PreSleepMiddleware(cfg, sleep_fn=slept.append)
        mw(_next())
        mw(_next())
        assert slept == []

    def test_delegates_to_next(self):
        cfg = PreSleepConfig(delay=0)
        mw = PreSleepMiddleware(cfg)
        result = mw(_next(exit_code=42))
        assert result.exit_code == 42

    def test_reset_clears_attempt_counter(self):
        slept: list[float] = []
        cfg = PreSleepConfig(delay=1.0, skip_first=True)
        mw = PreSleepMiddleware(cfg, sleep_fn=slept.append)
        mw(_next())
        mw.reset()
        mw(_next())  # should be treated as first attempt again
        assert slept == []

    def test_attempt_increments(self):
        cfg = PreSleepConfig(delay=0)
        mw = PreSleepMiddleware(cfg)
        assert mw.attempt == 0
        mw(_next())
        assert mw.attempt == 1
        mw(_next())
        assert mw.attempt == 2

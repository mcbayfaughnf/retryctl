"""Tests for retryctl.debounce."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from retryctl.debounce import DebounceActive, DebounceMiddleware, DebounceTracker
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    return r


def _next(result: CommandResult):
    return lambda _cmd: result


# ---------------------------------------------------------------------------
# DebounceTracker init
# ---------------------------------------------------------------------------

class TestDebounceTrackerInit:
    def test_zero_window_raises(self):
        with pytest.raises(ValueError):
            DebounceTracker(window=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            DebounceTracker(window=-1)

    def test_valid_window(self):
        t = DebounceTracker(window=1.0)
        assert t.window == 1.0


# ---------------------------------------------------------------------------
# DebounceTracker behaviour
# ---------------------------------------------------------------------------

class TestDebounceTrackerCheck:
    def test_first_check_passes(self):
        t = DebounceTracker(window=5.0)
        t.check("echo hi")  # should not raise

    def test_second_check_within_window_raises(self):
        t = DebounceTracker(window=5.0)
        t.record("echo hi")
        with pytest.raises(DebounceActive) as exc_info:
            t.check("echo hi")
        assert "echo hi" in str(exc_info.value)
        assert exc_info.value.command == "echo hi"
        assert exc_info.value.remaining > 0

    def test_check_passes_after_window_expires(self):
        t = DebounceTracker(window=0.05)
        t.record("cmd")
        time.sleep(0.06)
        t.check("cmd")  # should not raise

    def test_reset_single_key(self):
        t = DebounceTracker(window=5.0)
        t.record("cmd")
        t.reset("cmd")
        t.check("cmd")  # should not raise

    def test_reset_all_keys(self):
        t = DebounceTracker(window=5.0)
        t.record("cmd1")
        t.record("cmd2")
        t.reset()
        t.check("cmd1")
        t.check("cmd2")


# ---------------------------------------------------------------------------
# DebounceMiddleware
# ---------------------------------------------------------------------------

class TestDebounceMiddlewareSuccess:
    def test_delegates_to_next_on_first_call(self):
        res = _result()
        mw = DebounceMiddleware(window=5.0)
        out = mw("echo", _next(res))
        assert out is res

    def test_raises_on_second_call_within_window(self):
        mw = DebounceMiddleware(window=5.0)
        mw("echo", _next(_result()))
        with pytest.raises(DebounceActive):
            mw("echo", _next(_result()))

    def test_custom_key_fn_isolates_commands(self):
        # Both commands map to the same key → second call is debounced.
        mw = DebounceMiddleware(window=5.0, key_fn=lambda _: "shared")
        mw("cmd1", _next(_result()))
        with pytest.raises(DebounceActive):
            mw("cmd2", _next(_result()))

    def test_reset_clears_state(self):
        mw = DebounceMiddleware(window=5.0)
        mw("echo", _next(_result()))
        mw.reset("echo")
        mw("echo", _next(_result()))  # should not raise

    def test_tracker_property(self):
        mw = DebounceMiddleware(window=1.0)
        assert isinstance(mw.tracker, DebounceTracker)

"""Tests for retryctl.watchdog_middleware."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from retryctl.runner import CommandResult
from retryctl.watchdog import DeadlineExceeded, Watchdog
from retryctl.watchdog_middleware import WatchdogMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    return r


def _next(result: CommandResult):
    """Return a simple callable that always returns *result*."""
    return MagicMock(return_value=result)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestWatchdogMiddlewareSuccess:
    def test_delegates_to_next(self):
        wd = Watchdog()
        expected = _result(0)
        nxt = _next(expected)
        mw = WatchdogMiddleware(wd, nxt)
        got = mw(["echo", "hi"], attempt=1)
        assert got is expected
        nxt.assert_called_once_with(["echo", "hi"], 1)

    def test_calls_start_attempt_before_next(self):
        wd = Watchdog()
        call_order = []
        wd.start_attempt = lambda: call_order.append("start")
        nxt = MagicMock(side_effect=lambda *a, **kw: call_order.append("next") or _result())
        mw = WatchdogMiddleware(wd, nxt)
        mw(["ls"], attempt=1)
        assert call_order[0] == "start"
        assert "next" in call_order

    def test_exposes_watchdog_property(self):
        wd = Watchdog()
        mw = WatchdogMiddleware(wd, _next(_result()))
        assert mw.watchdog is wd


# ---------------------------------------------------------------------------
# Pre-call deadline already exceeded
# ---------------------------------------------------------------------------


class TestWatchdogMiddlewarePreCheck:
    def test_raises_before_calling_next_when_global_expired(self):
        wd = Watchdog(global_timeout=1.0)
        nxt = _next(_result())
        mw = WatchdogMiddleware(wd, nxt)
        future = wd._start + 5.0
        with patch("retryctl.watchdog.time.monotonic", return_value=future):
            with pytest.raises(DeadlineExceeded):
                mw(["cmd"], attempt=1)
        nxt.assert_not_called()


# ---------------------------------------------------------------------------
# Post-call deadline exceeded
# ---------------------------------------------------------------------------


class TestWatchdogMiddlewarePostCheck:
    def test_raises_after_next_when_deadline_crossed_during_execution(self):
        """Simulate a deadline that was crossed *while* the command ran."""
        wd = Watchdog(global_timeout=1.0)
        # The first check() call (pre) passes; subsequent calls fail.
        check_calls = [0]

        original_check = wd.check

        def fake_check():
            check_calls[0] += 1
            if check_calls[0] > 1:
                raise DeadlineExceeded("global", 0.0, 1.0)

        wd.check = fake_check
        nxt = _next(_result(0))
        mw = WatchdogMiddleware(wd, nxt)
        with pytest.raises(DeadlineExceeded):
            mw(["slow-cmd"], attempt=1)
        # next *was* called — the deadline expired after it returned
        nxt.assert_called_once()

    def test_deadline_exceeded_propagates_unchanged(self):
        wd = Watchdog()
        exc = DeadlineExceeded("attempt", 1.0, 2.0)
        nxt = MagicMock(side_effect=exc)
        mw = WatchdogMiddleware(wd, nxt)
        with pytest.raises(DeadlineExceeded) as exc_info:
            mw(["cmd"], attempt=1)
        assert exc_info.value is exc

"""Tests for retryctl.watchdog."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from retryctl.watchdog import DeadlineExceeded, Watchdog


# ---------------------------------------------------------------------------
# DeadlineExceeded
# ---------------------------------------------------------------------------


class TestDeadlineExceeded:
    def test_message_contains_scope(self):
        exc = DeadlineExceeded("global", 10.0, 11.0)
        assert "global" in str(exc)

    def test_stores_scope(self):
        exc = DeadlineExceeded("attempt", 5.0, 6.0)
        assert exc.scope == "attempt"

    def test_stores_deadline_and_now(self):
        exc = DeadlineExceeded("global", 3.0, 4.5)
        assert exc.deadline == pytest.approx(3.0)
        assert exc.now == pytest.approx(4.5)


# ---------------------------------------------------------------------------
# Watchdog — no limits
# ---------------------------------------------------------------------------


class TestWatchdogNoLimits:
    def test_check_never_raises_without_limits(self):
        wd = Watchdog()
        wd.check()  # must not raise

    def test_global_remaining_is_none(self):
        wd = Watchdog()
        assert wd.global_remaining() is None

    def test_attempt_remaining_is_none_without_timeout(self):
        wd = Watchdog()
        wd.start_attempt()
        assert wd.attempt_remaining() is None

    def test_elapsed_is_non_negative(self):
        wd = Watchdog()
        assert wd.elapsed() >= 0.0


# ---------------------------------------------------------------------------
# Watchdog — global timeout
# ---------------------------------------------------------------------------


class TestWatchdogGlobalTimeout:
    def test_check_passes_within_budget(self):
        wd = Watchdog(global_timeout=60.0)
        wd.check()  # well within budget

    def test_check_raises_when_expired(self):
        wd = Watchdog(global_timeout=1.0)
        # Simulate time having advanced past the deadline.
        future = wd._start + 2.0
        with patch("retryctl.watchdog.time.monotonic", return_value=future):
            with pytest.raises(DeadlineExceeded) as exc_info:
                wd.check()
        assert exc_info.value.scope == "global"

    def test_global_remaining_decreases(self):
        wd = Watchdog(global_timeout=100.0)
        r1 = wd.global_remaining()
        time.sleep(0.01)
        r2 = wd.global_remaining()
        assert r2 < r1

    def test_global_remaining_floors_at_zero(self):
        wd = Watchdog(global_timeout=0.001)
        time.sleep(0.05)
        assert wd.global_remaining() == 0.0


# ---------------------------------------------------------------------------
# Watchdog — attempt timeout
# ---------------------------------------------------------------------------


class TestWatchdogAttemptTimeout:
    def test_check_passes_within_attempt_budget(self):
        wd = Watchdog(attempt_timeout=60.0)
        wd.start_attempt()
        wd.check()

    def test_check_raises_when_attempt_expired(self):
        wd = Watchdog(attempt_timeout=1.0)
        wd.start_attempt()
        future = wd._attempt_start + 2.0
        with patch("retryctl.watchdog.time.monotonic", return_value=future):
            with pytest.raises(DeadlineExceeded) as exc_info:
                wd.check()
        assert exc_info.value.scope == "attempt"

    def test_no_raise_before_start_attempt(self):
        wd = Watchdog(attempt_timeout=0.001)
        # No start_attempt() called — should not raise.
        wd.check()

    def test_attempt_remaining_resets_on_new_attempt(self):
        wd = Watchdog(attempt_timeout=60.0)
        wd.start_attempt()
        r1 = wd.attempt_remaining()
        time.sleep(0.02)
        wd.start_attempt()  # reset
        r2 = wd.attempt_remaining()
        assert r2 > r1 - 0.005  # r2 should be close to full budget again

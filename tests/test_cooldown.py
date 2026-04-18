"""Tests for retryctl.cooldown."""
from __future__ import annotations

import pytest

from retryctl.cooldown import CooldownActive, CooldownPolicy, CooldownTracker


def _tracker(period: float = 5.0, command: str = "cmd") -> CooldownTracker:
    return CooldownTracker(policy=CooldownPolicy(period=period, command=command))


class TestCooldownPolicyInit:
    def test_zero_period_raises(self):
        with pytest.raises(ValueError):
            CooldownPolicy(period=0)

    def test_negative_period_raises(self):
        with pytest.raises(ValueError):
            CooldownPolicy(period=-1)

    def test_valid_period(self):
        p = CooldownPolicy(period=2.0)
        assert p.period == 2.0


class TestCooldownTrackerNoAttempt:
    def test_check_passes_before_any_attempt(self):
        t = _tracker()
        t.check()  # should not raise

    def test_last_attempt_is_none_initially(self):
        t = _tracker()
        assert t.last_attempt is None


class TestCooldownTrackerAfterRecord:
    def test_check_raises_immediately_after_record(self):
        t = _tracker(period=10.0)
        now = 1000.0
        t.record(now=now)
        with pytest.raises(CooldownActive) as exc_info:
            t.check(now=now + 1.0)
        assert exc_info.value.remaining == pytest.approx(9.0)

    def test_check_passes_after_period_elapsed(self):
        t = _tracker(period=5.0)
        t.record(now=1000.0)
        t.check(now=1005.1)  # should not raise

    def test_check_raises_exactly_at_period(self):
        t = _tracker(period=5.0)
        t.record(now=1000.0)
        with pytest.raises(CooldownActive):
            t.check(now=1004.9)

    def test_reset_clears_state(self):
        t = _tracker(period=10.0)
        t.record(now=1000.0)
        t.reset()
        t.check(now=1000.5)  # should not raise

    def test_cooldown_active_stores_command(self):
        t = _tracker(period=10.0, command="mycommand")
        t.record(now=0.0)
        with pytest.raises(CooldownActive) as exc_info:
            t.check(now=1.0)
        assert exc_info.value.command == "mycommand"

    def test_cooldown_active_message(self):
        t = _tracker(period=10.0, command="x")
        t.record(now=0.0)
        with pytest.raises(CooldownActive) as exc_info:
            t.check(now=2.0)
        assert "x" in str(exc_info.value)
        assert "8.00" in str(exc_info.value)

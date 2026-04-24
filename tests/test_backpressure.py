"""Tests for retryctl.backpressure."""
from __future__ import annotations

import pytest

from retryctl.backpressure import (
    BackpressureActive,
    BackpressurePolicy,
    BackpressureTracker,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _tracker(threshold: float = 0.8, window: int = 5) -> BackpressureTracker:
    return BackpressureTracker(policy=BackpressurePolicy(threshold=threshold, window=window))


# ---------------------------------------------------------------------------
# BackpressurePolicy
# ---------------------------------------------------------------------------

class TestBackpressurePolicyInit:
    def test_valid_policy(self):
        p = BackpressurePolicy(threshold=0.5, window=3)
        assert p.threshold == 0.5
        assert p.window == 3

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            BackpressurePolicy(threshold=0.0)

    def test_above_one_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            BackpressurePolicy(threshold=1.1)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            BackpressurePolicy(threshold=0.5, window=0)


# ---------------------------------------------------------------------------
# BackpressureActive
# ---------------------------------------------------------------------------

class TestBackpressureActive:
    def test_stores_load_and_threshold(self):
        exc = BackpressureActive(0.9, 0.8)
        assert exc.load == 0.9
        assert exc.threshold == 0.8

    def test_message_contains_load(self):
        exc = BackpressureActive(0.95, 0.8)
        assert "0.95" in str(exc)

    def test_message_contains_threshold(self):
        exc = BackpressureActive(0.95, 0.8)
        assert "0.80" in str(exc)


# ---------------------------------------------------------------------------
# BackpressureTracker
# ---------------------------------------------------------------------------

class TestBackpressureTrackerRecord:
    def test_invalid_load_below_zero(self):
        t = _tracker()
        with pytest.raises(ValueError):
            t.record(-0.1)

    def test_invalid_load_above_one(self):
        t = _tracker()
        with pytest.raises(ValueError):
            t.record(1.1)

    def test_window_truncates_old_samples(self):
        t = _tracker(window=3)
        for v in [0.1, 0.2, 0.3, 0.4]:
            t.record(v)
        assert len(t._samples) == 3
        assert t._samples == [0.2, 0.3, 0.4]


class TestBackpressureTrackerCurrentLoad:
    def test_no_samples_returns_zero(self):
        assert _tracker().current_load == 0.0

    def test_single_sample(self):
        t = _tracker()
        t.record(0.6)
        assert t.current_load == pytest.approx(0.6)

    def test_average_of_samples(self):
        t = _tracker()
        t.record(0.4)
        t.record(0.8)
        assert t.current_load == pytest.approx(0.6)


class TestBackpressureTrackerIsActive:
    def test_not_active_below_threshold(self):
        t = _tracker(threshold=0.8)
        t.record(0.5)
        assert not t.is_active

    def test_active_at_threshold(self):
        t = _tracker(threshold=0.8)
        t.record(0.8)
        assert t.is_active

    def test_active_above_threshold(self):
        t = _tracker(threshold=0.8)
        t.record(0.9)
        assert t.is_active


class TestBackpressureTrackerCheck:
    def test_no_raise_when_inactive(self):
        t = _tracker(threshold=0.8)
        t.record(0.5)
        t.check()  # should not raise

    def test_raises_when_active(self):
        t = _tracker(threshold=0.8)
        t.record(0.9)
        with pytest.raises(BackpressureActive):
            t.check()


class TestBackpressureTrackerReset:
    def test_clears_samples(self):
        t = _tracker()
        t.record(0.9)
        t.reset()
        assert t.current_load == 0.0
        assert not t.is_active

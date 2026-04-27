"""Tests for retryctl.watermark."""
import pytest
from retryctl.watermark import (
    WatermarkError,
    WatermarkPolicy,
    WatermarkTracker,
)


def _policy(high: int = 5, low: int = 2) -> WatermarkPolicy:
    return WatermarkPolicy(high=high, low=low)


def _tracker(high: int = 5, low: int = 2) -> WatermarkTracker:
    return WatermarkTracker(policy=_policy(high, low))


class TestWatermarkPolicyInit:
    def test_valid_policy(self):
        p = WatermarkPolicy(high=5, low=2)
        assert p.high == 5
        assert p.low == 2

    def test_zero_high_raises(self):
        with pytest.raises(WatermarkError):
            WatermarkPolicy(high=0, low=0)

    def test_negative_high_raises(self):
        with pytest.raises(WatermarkError):
            WatermarkPolicy(high=-1, low=0)

    def test_negative_low_raises(self):
        with pytest.raises(WatermarkError):
            WatermarkPolicy(high=5, low=-1)

    def test_low_equal_to_high_raises(self):
        with pytest.raises(WatermarkError):
            WatermarkPolicy(high=3, low=3)

    def test_low_greater_than_high_raises(self):
        with pytest.raises(WatermarkError):
            WatermarkPolicy(high=3, low=4)


class TestWatermarkTrackerDefaults:
    def test_count_starts_at_zero(self):
        t = _tracker()
        assert t.count == 0

    def test_peak_starts_at_zero(self):
        t = _tracker()
        assert t.peak == 0

    def test_above_high_is_false_initially(self):
        t = _tracker()
        assert t.above_high is False

    def test_below_low_is_true_initially(self):
        t = _tracker()
        assert t.below_low is True


class TestWatermarkTrackerRecord:
    def test_failure_increments_count(self):
        t = _tracker(high=5, low=2)
        t.record(1)
        assert t.count == 1

    def test_success_does_not_increment(self):
        t = _tracker()
        t.record(0)
        assert t.count == 0

    def test_above_high_set_when_count_reaches_high(self):
        t = _tracker(high=3, low=1)
        for _ in range(3):
            t.record(1)
        assert t.above_high is True

    def test_above_high_clears_after_dropping_to_low(self):
        t = _tracker(high=3, low=1)
        for _ in range(3):
            t.record(1)
        assert t.above_high is True
        # two successes to bring count from 3 -> 1 (low)
        t.record(0)
        t.record(0)
        assert t.above_high is False

    def test_peak_tracks_maximum(self):
        t = _tracker(high=10, low=2)
        for _ in range(6):
            t.record(1)
        t.record(0)
        assert t.peak == 6

    def test_reset_clears_all(self):
        t = _tracker(high=3, low=1)
        for _ in range(3):
            t.record(1)
        t.reset()
        assert t.count == 0
        assert t.peak == 0
        assert t.above_high is False

    def test_below_low_true_when_count_at_low(self):
        t = _tracker(high=5, low=2)
        t.record(1)
        t.record(1)
        assert t.below_low is True

    def test_below_low_false_when_count_above_low(self):
        t = _tracker(high=5, low=2)
        for _ in range(3):
            t.record(1)
        assert t.below_low is False

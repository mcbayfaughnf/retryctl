"""Tests for retryctl.shedding."""
from __future__ import annotations

import pytest

from retryctl.shedding import (
    LoadShedded,
    SheddingPolicy,
    SheddingTracker,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _tracker(threshold: float = 0.5, window: float = 60.0) -> SheddingTracker:
    return SheddingTracker(policy=SheddingPolicy(threshold=threshold, window=window))


# ---------------------------------------------------------------------------
# LoadShedded
# ---------------------------------------------------------------------------

class TestLoadShedded:
    def test_stores_load_and_threshold(self):
        exc = LoadShedded(load=0.9, threshold=0.8)
        assert exc.load == 0.9
        assert exc.threshold == 0.8

    def test_message_contains_load(self):
        exc = LoadShedded(load=0.75, threshold=0.5)
        assert "0.75" in str(exc)

    def test_message_contains_threshold(self):
        exc = LoadShedded(load=0.75, threshold=0.5)
        assert "0.50" in str(exc)


# ---------------------------------------------------------------------------
# SheddingPolicy
# ---------------------------------------------------------------------------

class TestSheddingPolicyInit:
    def test_valid_policy(self):
        p = SheddingPolicy(threshold=0.7)
        assert p.threshold == 0.7

    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            SheddingPolicy(threshold=0.0)

    def test_above_one_threshold_raises(self):
        with pytest.raises(ValueError, match="threshold"):
            SheddingPolicy(threshold=1.1)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            SheddingPolicy(threshold=0.5, window=0.0)


# ---------------------------------------------------------------------------
# SheddingTracker
# ---------------------------------------------------------------------------

class TestSheddingTrackerNoSamples:
    def test_load_is_zero_initially(self):
        t = _tracker()
        assert t.current_load() == 0.0

    def test_should_not_shed_when_empty(self):
        t = _tracker(threshold=0.5)
        assert t.should_shed() is False


class TestSheddingTrackerSamples:
    def test_all_successes_load_is_zero(self):
        t = _tracker()
        for _ in range(5):
            t.record(success=True)
        assert t.current_load() == 0.0

    def test_all_failures_load_is_one(self):
        t = _tracker()
        for _ in range(4):
            t.record(success=False)
        assert t.current_load() == 1.0

    def test_half_failures_load_is_half(self):
        t = _tracker()
        t.record(success=True)
        t.record(success=False)
        assert t.current_load() == pytest.approx(0.5)

    def test_should_shed_above_threshold(self):
        t = _tracker(threshold=0.5)
        t.record(success=False)
        t.record(success=False)
        t.record(success=True)
        # load = 2/3 ≈ 0.667 >= 0.5
        assert t.should_shed() is True

    def test_reset_clears_samples(self):
        t = _tracker()
        t.record(success=False)
        t.reset()
        assert t.current_load() == 0.0


class TestSheddingTrackerCustomLoadFn:
    def test_uses_custom_load_fn(self):
        policy = SheddingPolicy(threshold=0.5, load_fn=lambda: 0.9)
        t = SheddingTracker(policy=policy)
        assert t.current_load() == 0.9
        assert t.should_shed() is True

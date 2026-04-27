"""Tests for retryctl.window."""
from __future__ import annotations

import time
import pytest

from retryctl.window import WindowExceeded, WindowPolicy, WindowTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tracker(limit: int = 3, window: float = 1.0) -> WindowTracker:
    return WindowTracker(policy=WindowPolicy(limit=limit, window=window))


# ---------------------------------------------------------------------------
# WindowExceeded
# ---------------------------------------------------------------------------

class TestWindowExceeded:
    def test_stores_count_limit_window(self):
        exc = WindowExceeded(count=5, limit=3, window=2.0)
        assert exc.count == 5
        assert exc.limit == 3
        assert exc.window == 2.0

    def test_message_contains_limit(self):
        exc = WindowExceeded(count=4, limit=3, window=1.0)
        assert "3" in str(exc)

    def test_message_contains_window(self):
        exc = WindowExceeded(count=4, limit=3, window=5.5)
        assert "5.5" in str(exc)


# ---------------------------------------------------------------------------
# WindowPolicy
# ---------------------------------------------------------------------------

class TestWindowPolicyInit:
    def test_valid_policy(self):
        p = WindowPolicy(limit=5, window=10.0)
        assert p.limit == 5
        assert p.window == 10.0

    def test_zero_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            WindowPolicy(limit=0, window=1.0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            WindowPolicy(limit=-1, window=1.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            WindowPolicy(limit=1, window=0.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            WindowPolicy(limit=1, window=-5.0)


# ---------------------------------------------------------------------------
# WindowTracker
# ---------------------------------------------------------------------------

class TestWindowTrackerCheck:
    def test_first_attempt_succeeds(self):
        t = _tracker(limit=2)
        t.check()  # should not raise

    def test_up_to_limit_succeeds(self):
        t = _tracker(limit=3)
        for _ in range(3):
            t.check()

    def test_exceeds_limit_raises(self):
        t = _tracker(limit=2)
        t.check()
        t.check()
        with pytest.raises(WindowExceeded):
            t.check()

    def test_current_count_increments(self):
        t = _tracker(limit=5)
        assert t.current_count == 0
        t.check()
        assert t.current_count == 1
        t.check()
        assert t.current_count == 2

    def test_old_timestamps_evicted(self):
        t = _tracker(limit=2, window=0.05)
        t.check()
        t.check()
        time.sleep(0.1)
        # window has passed; both old entries should be evicted
        t.check()  # should not raise
        assert t.current_count == 1

    def test_reset_clears_count(self):
        t = _tracker(limit=3)
        t.check()
        t.check()
        t.reset()
        assert t.current_count == 0

    def test_reset_allows_reuse(self):
        t = _tracker(limit=2)
        t.check()
        t.check()
        t.reset()
        t.check()  # should not raise after reset

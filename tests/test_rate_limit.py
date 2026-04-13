"""Tests for retryctl.rate_limit and retryctl.rate_limit_middleware."""
from __future__ import annotations

import pytest

from retryctl.rate_limit import RateLimitExceeded, SlidingWindowCounter
from retryctl.rate_limit_middleware import RateLimitMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _counter(limit: int = 3, window: float = 60.0) -> SlidingWindowCounter:
    return SlidingWindowCounter(limit=limit, window=window)


# ---------------------------------------------------------------------------
# SlidingWindowCounter – construction
# ---------------------------------------------------------------------------

class TestSlidingWindowCounterInit:
    def test_zero_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            SlidingWindowCounter(limit=0, window=10.0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            SlidingWindowCounter(limit=-1, window=10.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            SlidingWindowCounter(limit=5, window=0.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            SlidingWindowCounter(limit=5, window=-1.0)


# ---------------------------------------------------------------------------
# SlidingWindowCounter – allow / check
# ---------------------------------------------------------------------------

class TestSlidingWindowCounterAllow:
    def test_allows_up_to_limit(self):
        c = _counter(limit=3, window=60.0)
        now = 0.0
        assert c.allow(now) is True
        assert c.allow(now) is True
        assert c.allow(now) is True

    def test_blocks_over_limit(self):
        c = _counter(limit=2, window=60.0)
        c.allow(0.0)
        c.allow(0.0)
        assert c.allow(0.0) is False

    def test_evicts_old_timestamps(self):
        c = _counter(limit=2, window=10.0)
        c.allow(0.0)
        c.allow(0.0)
        # Both calls are now outside the window
        assert c.allow(11.0) is True

    def test_check_raises_on_exceed(self):
        c = _counter(limit=1, window=60.0)
        c.allow(0.0)
        with pytest.raises(RateLimitExceeded) as exc_info:
            c.check(0.0)
        assert exc_info.value.limit == 1
        assert exc_info.value.window == 60.0

    def test_current_count_reflects_window(self):
        c = _counter(limit=5, window=10.0)
        c.allow(0.0)
        c.allow(0.0)
        assert c.current_count == 0  # monotonic time has advanced past window


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware:
    def _mw(self, limit: int = 3, window: float = 60.0) -> RateLimitMiddleware:
        return RateLimitMiddleware(limit=limit, window=window)

    def test_delegates_when_under_limit(self):
        mw = self._mw(limit=5)
        sentinel = object()
        result = mw(lambda: sentinel)
        assert result is sentinel

    def test_raises_when_limit_exceeded(self):
        counter = SlidingWindowCounter(limit=1, window=60.0)
        counter.allow(0.0)  # consume the single slot
        mw = RateLimitMiddleware(limit=1, window=60.0, counter=counter)
        with pytest.raises(RateLimitExceeded):
            mw(lambda: None)

    def test_reset_clears_state(self):
        mw = self._mw(limit=1)
        mw(lambda: None)  # consume slot
        mw.reset()
        called = []
        mw(lambda: called.append(True))
        assert called

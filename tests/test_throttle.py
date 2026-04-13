"""Tests for retryctl.throttle."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from retryctl.throttle import ThrottleExceeded, TokenBucket


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bucket(rate: float = 1.0, capacity: float = 1.0) -> TokenBucket:
    return TokenBucket(rate=rate, capacity=capacity)


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

class TestTokenBucketInit:
    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="rate"):
            TokenBucket(rate=-1.0, capacity=1.0)

    def test_zero_rate_raises(self):
        with pytest.raises(ValueError, match="rate"):
            TokenBucket(rate=0.0, capacity=1.0)

    def test_negative_capacity_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            TokenBucket(rate=1.0, capacity=-1.0)

    def test_starts_full(self):
        b = _bucket(rate=2.0, capacity=5.0)
        assert b.available() == pytest.approx(5.0, abs=0.05)


# ---------------------------------------------------------------------------
# consume – non-blocking
# ---------------------------------------------------------------------------

class TestConsumeNonBlocking:
    def test_consume_when_full_succeeds(self):
        b = _bucket(capacity=3.0)
        b.consume(block=False)  # should not raise

    def test_consume_depletes_tokens(self):
        b = _bucket(rate=1.0, capacity=2.0)
        b.consume(tokens=1.0, block=False)
        assert b.available() < 2.0

    def test_over_consume_raises_throttle_exceeded(self):
        b = _bucket(rate=1.0, capacity=1.0)
        b.consume(tokens=1.0, block=False)  # drain
        with pytest.raises(ThrottleExceeded):
            b.consume(block=False)

    def test_throttle_exceeded_has_retry_after(self):
        b = _bucket(rate=1.0, capacity=1.0)
        b.consume(block=False)
        exc = pytest.raises(ThrottleExceeded, b.consume, block=False)
        assert exc.value.retry_after > 0

    def test_throttle_exceeded_message(self):
        b = _bucket(rate=1.0, capacity=1.0)
        b.consume(block=False)
        with pytest.raises(ThrottleExceeded, match="Throttle exceeded"):
            b.consume(block=False)


# ---------------------------------------------------------------------------
# consume – blocking (mocked sleep)
# ---------------------------------------------------------------------------

class TestConsumeBlocking:
    def test_blocking_calls_sleep_when_empty(self):
        b = _bucket(rate=1.0, capacity=1.0)
        b.consume(block=False)  # drain
        with patch("retryctl.throttle.time.sleep") as mock_sleep:
            b.consume(block=True)
        mock_sleep.assert_called_once()

    def test_blocking_sleep_duration_positive(self):
        b = _bucket(rate=0.5, capacity=1.0)
        b.consume(block=False)  # drain
        with patch("retryctl.throttle.time.sleep") as mock_sleep:
            b.consume(block=True)
        (wait,), _ = mock_sleep.call_args
        assert wait > 0


# ---------------------------------------------------------------------------
# retry_after
# ---------------------------------------------------------------------------

class TestRetryAfter:
    def test_full_bucket_returns_zero(self):
        b = _bucket(rate=1.0, capacity=1.0)
        assert b.retry_after() == pytest.approx(0.0, abs=0.01)

    def test_empty_bucket_returns_positive(self):
        b = _bucket(rate=1.0, capacity=1.0)
        b.consume(block=False)
        assert b.retry_after() > 0

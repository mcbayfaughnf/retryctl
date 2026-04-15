"""Tests for retryctl.retry_budget."""
from __future__ import annotations

import time

import pytest

from retryctl.retry_budget import BudgetExhausted, RetryBudget


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _budget(limit: int = 3, window: float = 60.0) -> RetryBudget:
    return RetryBudget(limit=limit, window=window)


# ---------------------------------------------------------------------------
# BudgetExhausted
# ---------------------------------------------------------------------------

class TestBudgetExhausted:
    def test_message_contains_used(self):
        exc = BudgetExhausted(used=5, limit=5, window=30.0)
        assert "5" in str(exc)

    def test_message_contains_limit(self):
        exc = BudgetExhausted(used=5, limit=5, window=30.0)
        assert "5" in str(exc)

    def test_message_contains_window(self):
        exc = BudgetExhausted(used=3, limit=3, window=120.0)
        assert "120" in str(exc)

    def test_stores_attributes(self):
        exc = BudgetExhausted(used=2, limit=4, window=10.0)
        assert exc.used == 2
        assert exc.limit == 4
        assert exc.window == 10.0


# ---------------------------------------------------------------------------
# RetryBudget initialisation
# ---------------------------------------------------------------------------

class TestRetryBudgetInit:
    def test_zero_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            RetryBudget(limit=0, window=60.0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            RetryBudget(limit=-1, window=60.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            RetryBudget(limit=3, window=0.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            RetryBudget(limit=3, window=-5.0)


# ---------------------------------------------------------------------------
# RetryBudget.consume
# ---------------------------------------------------------------------------

class TestRetryBudgetConsume:
    def test_consume_within_limit_succeeds(self):
        b = _budget(limit=3)
        b.consume()
        b.consume()
        b.consume()
        assert b.used == 3

    def test_consume_over_limit_raises(self):
        b = _budget(limit=2)
        b.consume()
        b.consume()
        with pytest.raises(BudgetExhausted):
            b.consume()

    def test_remaining_decrements_on_consume(self):
        b = _budget(limit=5)
        assert b.remaining() == 5
        b.consume()
        assert b.remaining() == 4

    def test_reset_clears_budget(self):
        b = _budget(limit=2)
        b.consume()
        b.consume()
        b.reset()
        assert b.used == 0
        assert b.remaining() == 2

    def test_old_entries_evicted_after_window(self):
        """Entries older than the window should not count toward the budget."""
        b = RetryBudget(limit=2, window=0.05)
        b.consume()
        b.consume()
        # Wait for the window to expire
        time.sleep(0.1)
        # Should be able to consume again without raising
        b.consume()
        assert b.used == 1

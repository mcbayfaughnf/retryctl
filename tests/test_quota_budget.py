"""Tests for retryctl.quota_budget."""
import pytest

from retryctl.quota_budget import (
    QuotaBudget,
    QuotaBudgetExhausted,
    QuotaBudgetPolicy,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _budget(max_attempts=3, max_cost=0.0, cost_per_attempt=1.0) -> QuotaBudget:
    policy = QuotaBudgetPolicy(
        max_attempts=max_attempts,
        max_cost=max_cost,
        cost_per_attempt=cost_per_attempt,
    )
    return QuotaBudget(policy=policy)


# ---------------------------------------------------------------------------
# QuotaBudgetPolicy validation
# ---------------------------------------------------------------------------

class TestQuotaBudgetPolicyInit:
    def test_zero_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            QuotaBudgetPolicy(max_attempts=0)

    def test_negative_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            QuotaBudgetPolicy(max_attempts=-1)

    def test_negative_max_cost_raises(self):
        with pytest.raises(ValueError, match="max_cost"):
            QuotaBudgetPolicy(max_attempts=5, max_cost=-1.0)

    def test_zero_cost_per_attempt_raises(self):
        with pytest.raises(ValueError, match="cost_per_attempt"):
            QuotaBudgetPolicy(max_attempts=5, cost_per_attempt=0.0)

    def test_valid_policy(self):
        p = QuotaBudgetPolicy(max_attempts=5, max_cost=10.0, cost_per_attempt=2.0)
        assert p.max_attempts == 5


# ---------------------------------------------------------------------------
# QuotaBudget consume / remaining
# ---------------------------------------------------------------------------

class TestQuotaBudgetConsume:
    def test_initial_attempts_zero(self):
        b = _budget(max_attempts=3)
        assert b.attempts == 0

    def test_consume_increments_attempts(self):
        b = _budget(max_attempts=3)
        b.consume()
        assert b.attempts == 1

    def test_remaining_decrements(self):
        b = _budget(max_attempts=3)
        b.consume()
        assert b.remaining() == 2

    def test_exceeding_attempt_limit_raises(self):
        b = _budget(max_attempts=2)
        b.consume()
        b.consume()
        with pytest.raises(QuotaBudgetExhausted) as exc_info:
            b.consume()
        assert "attempt limit" in str(exc_info.value)
        assert exc_info.value.used == 2
        assert exc_info.value.limit == 2

    def test_cost_accumulates(self):
        b = _budget(max_attempts=5, cost_per_attempt=2.5)
        b.consume()
        b.consume()
        assert b.total_cost == pytest.approx(5.0)

    def test_exceeding_cost_limit_raises(self):
        b = _budget(max_attempts=10, max_cost=3.0, cost_per_attempt=2.0)
        b.consume()  # cost = 2.0
        with pytest.raises(QuotaBudgetExhausted) as exc_info:
            b.consume()  # projected = 4.0 > 3.0
        assert "cost limit" in str(exc_info.value)

    def test_zero_max_cost_disables_cost_check(self):
        b = _budget(max_attempts=5, max_cost=0.0, cost_per_attempt=100.0)
        for _ in range(5):
            b.consume()  # should not raise on cost
        assert b.attempts == 5

    def test_reset_clears_counters(self):
        b = _budget(max_attempts=3)
        b.consume()
        b.consume()
        b.reset()
        assert b.attempts == 0
        assert b.total_cost == 0.0
        assert b.remaining() == 3


# ---------------------------------------------------------------------------
# QuotaBudgetExhausted message
# ---------------------------------------------------------------------------

class TestQuotaBudgetExhausted:
    def test_message_contains_reason(self):
        exc = QuotaBudgetExhausted("attempt limit", 5, 5)
        assert "attempt limit" in str(exc)

    def test_stores_used_and_limit(self):
        exc = QuotaBudgetExhausted("cost limit", 10, 8)
        assert exc.used == 10
        assert exc.limit == 8

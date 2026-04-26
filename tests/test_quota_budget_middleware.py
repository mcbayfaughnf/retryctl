"""Tests for retryctl.quota_budget_middleware."""
import pytest

from retryctl.quota_budget import QuotaBudgetExhausted, QuotaBudgetPolicy
from retryctl.quota_budget_middleware import QuotaBudgetMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0) -> CommandResult:
    r = CommandResult.__new__(CommandResult)
    r.command = ["echo", "hi"]
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    r.attempts = 1
    r.elapsed = 0.01
    return r


def _next(exit_code: int = 0):
    def fn(*args, **kwargs):
        return _result(exit_code)
    return fn


def _middleware(max_attempts=3, max_cost=0.0, cost_per_attempt=1.0):
    return QuotaBudgetMiddleware(
        max_attempts=max_attempts,
        max_cost=max_cost,
        cost_per_attempt=cost_per_attempt,
    )


# ---------------------------------------------------------------------------
# success path
# ---------------------------------------------------------------------------

class TestQuotaBudgetMiddlewareSuccess:
    def test_delegates_to_next(self):
        mw = _middleware(max_attempts=5)
        result = mw(_next(0))
        assert result.exit_code == 0

    def test_increments_attempts(self):
        mw = _middleware(max_attempts=5)
        mw(_next())
        mw(_next())
        assert mw.attempts == 2

    def test_remaining_decrements(self):
        mw = _middleware(max_attempts=4)
        mw(_next())
        assert mw.remaining() == 3

    def test_total_cost_accumulates(self):
        mw = _middleware(max_attempts=5, cost_per_attempt=2.0)
        mw(_next())
        mw(_next())
        assert mw.total_cost == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# exhaustion
# ---------------------------------------------------------------------------

class TestQuotaBudgetMiddlewareExhausted:
    def test_raises_after_max_attempts(self):
        mw = _middleware(max_attempts=2)
        mw(_next())
        mw(_next())
        with pytest.raises(QuotaBudgetExhausted):
            mw(_next())

    def test_raises_on_cost_breach(self):
        mw = _middleware(max_attempts=10, max_cost=3.0, cost_per_attempt=2.0)
        mw(_next())  # cost = 2.0
        with pytest.raises(QuotaBudgetExhausted):
            mw(_next())  # projected = 4.0

    def test_reset_allows_reuse(self):
        mw = _middleware(max_attempts=1)
        mw(_next())
        mw.reset()
        result = mw(_next(0))
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# policy constructor path
# ---------------------------------------------------------------------------

class TestQuotaBudgetMiddlewareWithPolicy:
    def test_accepts_explicit_policy(self):
        policy = QuotaBudgetPolicy(max_attempts=7, cost_per_attempt=0.5)
        mw = QuotaBudgetMiddleware(policy=policy)
        mw(_next())
        assert mw.budget.policy.max_attempts == 7

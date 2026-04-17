"""Tests for retryctl.cost_middleware."""
import pytest
from retryctl.cost import CostExceeded
from retryctl.cost_middleware import CostMiddleware
from retryctl.runner import CommandResult


def _result(code: int = 0) -> CommandResult:
    r = object.__new__(CommandResult)
    r.command = ["echo"]
    r.exit_code = code
    r.stdout = ""
    r.stderr = ""
    r.attempts = 1
    r.elapsed = 0.0
    return r


def _next(code: int = 0):
    def fn():
        return _result(code)
    return fn


class TestCostMiddlewareSuccess:
    def test_delegates_to_next(self):
        mw = CostMiddleware(cost_per_attempt=1.0, budget=5.0)
        result = mw(_next(0))
        assert result.exit_code == 0

    def test_accumulates_cost(self):
        mw = CostMiddleware(cost_per_attempt=2.0, budget=10.0)
        mw(_next())
        mw(_next())
        assert mw.total_cost == pytest.approx(4.0)

    def test_remaining_decreases(self):
        mw = CostMiddleware(cost_per_attempt=1.0, budget=3.0)
        mw(_next())
        assert mw.remaining() == pytest.approx(2.0)

    def test_reset_clears_cost(self):
        mw = CostMiddleware(cost_per_attempt=1.0, budget=5.0)
        mw(_next())
        mw.reset()
        assert mw.total_cost == pytest.approx(0.0)


class TestCostMiddlewareBudgetExceeded:
    def test_raises_when_budget_exceeded(self):
        mw = CostMiddleware(cost_per_attempt=1.0, budget=2.0)
        mw(_next())
        mw(_next())
        with pytest.raises(CostExceeded):
            mw(_next())

    def test_unlimited_budget_never_raises(self):
        mw = CostMiddleware(cost_per_attempt=1.0, budget=None)
        for _ in range(100):
            mw(_next())
        assert mw.remaining() is None

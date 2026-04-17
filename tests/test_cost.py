"""Tests for retryctl.cost."""
import pytest
from retryctl.cost import CostPolicy, CostAccumulator, CostExceeded


@pytest.fixture()
def _policy():
    return CostPolicy(cost_per_attempt=1.0, budget=3.0)


@pytest.fixture()
def _acc(_policy):
    return CostAccumulator(policy=_policy)


class TestCostPolicyInit:
    def test_negative_cost_raises(self):
        with pytest.raises(ValueError, match="cost_per_attempt"):
            CostPolicy(cost_per_attempt=-1.0)

    def test_zero_budget_raises(self):
        with pytest.raises(ValueError, match="budget"):
            CostPolicy(budget=0.0)

    def test_none_budget_is_unlimited(self):
        p = CostPolicy(budget=None)
        assert p.budget is None


class TestCostAccumulatorCharge:
    def test_charge_increments_total(self, _acc):
        _acc.charge()
        assert _acc.total == pytest.approx(1.0)

    def test_charge_returns_amount(self, _acc):
        amount = _acc.charge(multiplier=2.0)
        assert amount == pytest.approx(2.0)

    def test_exceeds_budget_raises(self, _acc):
        _acc.charge()
        _acc.charge()
        _acc.charge()
        with pytest.raises(CostExceeded) as exc_info:
            _acc.charge()
        assert exc_info.value.limit == pytest.approx(3.0)

    def test_reset_clears_total(self, _acc):
        _acc.charge()
        _acc.reset()
        assert _acc.total == pytest.approx(0.0)

    def test_remaining_decreases(self, _acc):
        _acc.charge()
        assert _acc.remaining() == pytest.approx(2.0)

    def test_remaining_none_when_unlimited(self):
        acc = CostAccumulator(policy=CostPolicy(budget=None))
        assert acc.remaining() is None


class TestCostExceeded:
    def test_message_contains_used_and_limit(self):
        exc = CostExceeded(used=4.0, limit=3.0)
        assert "4" in str(exc)
        assert "3" in str(exc)

    def test_stores_fields(self):
        exc = CostExceeded(used=5.5, limit=3.0)
        assert exc.used == pytest.approx(5.5)
        assert exc.limit == pytest.approx(3.0)

"""Tests for retryctl.jitter_budget."""
from __future__ import annotations

import threading
import pytest

from retryctl.jitter_budget import BudgetExhausted, JitterBudget


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _budget(limit: float = 1.0) -> JitterBudget:
    return JitterBudget(limit=limit)


# ---------------------------------------------------------------------------
# BudgetExhausted
# ---------------------------------------------------------------------------

class TestBudgetExhausted:
    def test_message_contains_used(self):
        exc = BudgetExhausted(used=0.8, limit=1.0)
        assert "0.800" in str(exc)

    def test_message_contains_limit(self):
        exc = BudgetExhausted(used=0.8, limit=1.0)
        assert "1.000" in str(exc)

    def test_stores_used_and_limit(self):
        exc = BudgetExhausted(used=0.5, limit=2.0)
        assert exc.used == 0.5
        assert exc.limit == 2.0


# ---------------------------------------------------------------------------
# JitterBudget initialisation
# ---------------------------------------------------------------------------

class TestJitterBudgetInit:
    def test_zero_limit_raises(self):
        with pytest.raises(ValueError):
            JitterBudget(limit=0.0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError):
            JitterBudget(limit=-1.0)

    def test_initial_used_is_zero(self):
        assert _budget().used == 0.0

    def test_initial_remaining_equals_limit(self):
        b = _budget(limit=2.5)
        assert b.remaining == pytest.approx(2.5)


# ---------------------------------------------------------------------------
# consume
# ---------------------------------------------------------------------------

class TestJitterBudgetConsume:
    def test_returns_amount_when_within_budget(self):
        b = _budget(limit=1.0)
        assert b.consume(0.3) == pytest.approx(0.3)

    def test_used_increases_after_consume(self):
        b = _budget(limit=1.0)
        b.consume(0.4)
        assert b.used == pytest.approx(0.4)

    def test_remaining_decreases_after_consume(self):
        b = _budget(limit=1.0)
        b.consume(0.4)
        assert b.remaining == pytest.approx(0.6)

    def test_caps_at_remaining_budget(self):
        b = _budget(limit=1.0)
        b.consume(0.8)
        actual = b.consume(0.5)  # only 0.2 left
        assert actual == pytest.approx(0.2)
        assert b.used == pytest.approx(1.0)

    def test_raises_when_budget_exhausted(self):
        b = _budget(limit=0.5)
        b.consume(0.5)
        with pytest.raises(BudgetExhausted):
            b.consume(0.1)

    def test_negative_amount_raises(self):
        b = _budget()
        with pytest.raises(ValueError):
            b.consume(-0.1)

    def test_zero_amount_is_noop(self):
        b = _budget(limit=1.0)
        actual = b.consume(0.0)
        assert actual == 0.0
        assert b.used == 0.0


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestJitterBudgetReset:
    def test_reset_clears_used(self):
        b = _budget(limit=1.0)
        b.consume(0.7)
        b.reset()
        assert b.used == 0.0

    def test_reset_restores_remaining(self):
        b = _budget(limit=1.0)
        b.consume(0.7)
        b.reset()
        assert b.remaining == pytest.approx(1.0)

    def test_consume_works_after_reset(self):
        b = _budget(limit=0.5)
        b.consume(0.5)
        b.reset()
        assert b.consume(0.3) == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestJitterBudgetThreadSafety:
    def test_concurrent_consumes_do_not_exceed_limit(self):
        limit = 1.0
        b = JitterBudget(limit=limit)
        errors: list[Exception] = []

        def worker():
            try:
                b.consume(0.1)
            except BudgetExhausted:
                pass
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert b.used <= pytest.approx(limit)

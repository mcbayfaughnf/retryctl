"""Unit tests for retryctl.circuit_breaker_middleware."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from retryctl.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState
from retryctl.circuit_breaker_middleware import CircuitBreakerMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    return r


def _middleware(threshold: int = 3, recovery: float = 30.0):
    breaker = CircuitBreaker(name="test", failure_threshold=threshold, recovery_timeout=recovery)
    next_fn = MagicMock(return_value=_result(0))
    mw = CircuitBreakerMiddleware(breaker=breaker, next_fn=next_fn)
    return mw, breaker, next_fn


class TestCircuitBreakerMiddlewareSuccess:
    def test_delegates_to_next_on_closed(self):
        mw, _, next_fn = _middleware()
        mw(["echo", "hi"])
        next_fn.assert_called_once_with(["echo", "hi"])

    def test_records_success_on_zero_exit(self):
        mw, breaker, _ = _middleware()
        mw(["true"])
        assert breaker._failures == 0
        assert breaker.state is CircuitState.CLOSED

    def test_returns_result_from_next(self):
        mw, _, next_fn = _middleware()
        expected = _result(0)
        next_fn.return_value = expected
        assert mw(["cmd"]) is expected


class TestCircuitBreakerMiddlewareFailure:
    def test_records_failure_on_nonzero_exit(self):
        mw, breaker, next_fn = _middleware()
        next_fn.return_value = _result(1)
        mw(["bad"])
        assert breaker._failures == 1

    def test_opens_circuit_after_threshold(self):
        mw, breaker, next_fn = _middleware(threshold=2)
        next_fn.return_value = _result(1)
        mw(["bad"])
        mw(["bad"])
        assert breaker.state is CircuitState.OPEN

    def test_raises_when_circuit_open(self):
        mw, breaker, next_fn = _middleware(threshold=2)
        next_fn.return_value = _result(1)
        mw(["bad"])
        mw(["bad"])
        with pytest.raises(CircuitOpenError):
            mw(["bad"])

    def test_next_not_called_when_open(self):
        mw, _, next_fn = _middleware(threshold=2)
        next_fn.return_value = _result(1)
        mw(["bad"])
        mw(["bad"])
        call_count_before = next_fn.call_count
        with pytest.raises(CircuitOpenError):
            mw(["bad"])
        assert next_fn.call_count == call_count_before


class TestCircuitBreakerMiddlewareReset:
    def test_reset_allows_requests_again(self):
        mw, _, next_fn = _middleware(threshold=2)
        next_fn.return_value = _result(1)
        mw(["bad"])
        mw(["bad"])
        mw.reset()
        next_fn.return_value = _result(0)
        result = mw(["ok"])
        assert result.exit_code == 0

    def test_state_property_delegates(self):
        mw, breaker, _ = _middleware()
        assert mw.state is breaker.state

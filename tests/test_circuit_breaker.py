"""Unit tests for retryctl.circuit_breaker."""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from retryctl.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


def _breaker(**kw) -> CircuitBreaker:
    return CircuitBreaker(name="test", failure_threshold=3, recovery_timeout=10.0, **kw)


class TestCircuitBreakerInit:
    def test_defaults_to_closed(self):
        cb = _breaker()
        assert cb.state is CircuitState.CLOSED

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreaker(name="x", failure_threshold=0)

    def test_invalid_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreaker(name="x", recovery_timeout=0.0)


class TestCircuitBreakerTransitions:
    def test_opens_after_threshold(self):
        cb = _breaker()
        for _ in range(3):
            cb.record_failure()
        assert cb.state is CircuitState.OPEN

    def test_does_not_open_below_threshold(self):
        cb = _breaker()
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED

    def test_success_resets_to_closed(self):
        cb = _breaker()
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.state is CircuitState.CLOSED
        assert cb._failures == 0

    def test_half_open_after_recovery_timeout(self):
        cb = _breaker(recovery_timeout=1.0)
        for _ in range(3):
            cb.record_failure()
        assert cb.state is CircuitState.OPEN
        with patch("retryctl.circuit_breaker.time.monotonic", return_value=time.monotonic() + 2.0):
            assert cb.state is CircuitState.HALF_OPEN

    def test_half_open_opens_on_failure(self):
        cb = _breaker(recovery_timeout=0.01)
        for _ in range(3):
            cb.record_failure()
        time.sleep(0.02)
        assert cb.state is CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state is CircuitState.OPEN

    def test_reset_closes_circuit(self):
        cb = _breaker()
        for _ in range(3):
            cb.record_failure()
        cb.reset()
        assert cb.state is CircuitState.CLOSED
        assert cb._failures == 0


class TestAllowRequest:
    def test_allows_when_closed(self):
        assert _breaker().allow_request() is True

    def test_blocks_when_open(self):
        cb = _breaker()
        for _ in range(3):
            cb.record_failure()
        assert cb.allow_request() is False


class TestCircuitOpenError:
    def test_message_contains_name(self):
        err = CircuitOpenError("svc", time.monotonic() + 5)
        assert "svc" in str(err)

    def test_stores_name(self):
        err = CircuitOpenError("svc", time.monotonic() + 5)
        assert err.name == "svc"

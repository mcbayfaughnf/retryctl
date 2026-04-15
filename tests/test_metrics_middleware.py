"""Tests for retryctl.metrics_middleware."""
from unittest.mock import MagicMock

import pytest

from retryctl.metrics import MetricsCollector
from retryctl.metrics_middleware import MetricsMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    return r


def _next(result: CommandResult):
    def handler(*args, **kwargs):
        return result
    return handler


def _middleware(
    success_codes: frozenset[int] | None = None,
) -> tuple[MetricsMiddleware, MetricsCollector]:
    collector = MetricsCollector()
    mw = MetricsMiddleware(collector, success_codes=success_codes)
    return mw, collector


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------

class TestMetricsMiddlewareSuccess:
    def test_increments_attempts(self):
        mw, col = _middleware()
        mw(_next(_result(0)))
        assert col.get("attempts") == 1

    def test_increments_successes_on_zero(self):
        mw, col = _middleware()
        mw(_next(_result(0)))
        assert col.get("successes") == 1

    def test_does_not_increment_failures_on_success(self):
        mw, col = _middleware()
        mw(_next(_result(0)))
        assert col.get("failures") == 0

    def test_custom_success_codes(self):
        mw, col = _middleware(success_codes=frozenset({0, 2}))
        mw(_next(_result(2)))
        assert col.get("successes") == 1
        assert col.get("failures") == 0


# ---------------------------------------------------------------------------
# Failure path
# ---------------------------------------------------------------------------

class TestMetricsMiddlewareFailure:
    def test_increments_failures_on_nonzero(self):
        mw, col = _middleware()
        mw(_next(_result(1)))
        assert col.get("failures") == 1

    def test_increments_retries_on_failure(self):
        mw, col = _middleware()
        mw(_next(_result(1)))
        assert col.get("retries") == 1

    def test_does_not_increment_successes_on_failure(self):
        mw, col = _middleware()
        mw(_next(_result(1)))
        assert col.get("successes") == 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestMetricsMiddlewareHelpers:
    def test_collector_property(self):
        mw, col = _middleware()
        assert mw.collector is col

    def test_reset_delegates_to_collector(self):
        mw, col = _middleware()
        col.increment("attempts", 5)
        mw.reset()
        assert col.get("attempts") == 0

    def test_returns_result_unchanged(self):
        mw, _ = _middleware()
        expected = _result(0)
        actual = mw(_next(expected))
        assert actual is expected

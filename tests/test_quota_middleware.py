"""Tests for retryctl.quota_middleware."""
import pytest
from unittest.mock import MagicMock
from retryctl.quota import QuotaExceeded, QuotaRegistry
from retryctl.quota_middleware import QuotaMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    return r


def _next(result: CommandResult):
    return MagicMock(return_value=result)


def _middleware(limit: int = 3, window: float = 60.0) -> QuotaMiddleware:
    return QuotaMiddleware(key="cmd", limit=limit, window=window)


class TestQuotaMiddlewareSuccess:
    def test_delegates_to_next(self):
        result = _result()
        nxt = _next(result)
        mw = _middleware()
        out = mw(nxt)
        nxt.assert_called_once()
        assert out is result

    def test_increments_current(self):
        mw = _middleware(limit=5)
        mw(_next(_result()))
        mw(_next(_result()))
        assert mw.current() == 2

    def test_reset_zeroes_count(self):
        mw = _middleware(limit=5)
        mw(_next(_result()))
        mw.reset()
        assert mw.current() == 0


class TestQuotaMiddlewareExceeded:
    def test_raises_quota_exceeded_at_limit(self):
        mw = _middleware(limit=2)
        mw(_next(_result()))
        mw(_next(_result()))
        with pytest.raises(QuotaExceeded):
            mw(_next(_result()))

    def test_next_not_called_when_exceeded(self):
        mw = _middleware(limit=1)
        mw(_next(_result()))
        nxt = _next(_result())
        with pytest.raises(QuotaExceeded):
            mw(nxt)
        nxt.assert_not_called()

    def test_shared_registry_across_instances(self):
        registry = QuotaRegistry()
        mw1 = QuotaMiddleware(key="shared", limit=2, window=60.0, registry=registry)
        mw2 = QuotaMiddleware(key="shared", limit=2, window=60.0, registry=registry)
        mw1(_next(_result()))
        mw2(_next(_result()))
        with pytest.raises(QuotaExceeded):
            mw1(_next(_result()))

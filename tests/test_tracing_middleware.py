"""Tests for retryctl.tracing_middleware."""
import pytest
from unittest.mock import MagicMock
from retryctl.runner import CommandResult
from retryctl.tracing import Tracer
from retryctl.tracing_middleware import TracingMiddleware


def _result(exit_code: int = 0, attempts: int = 1) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    r.attempts = attempts
    r.command = ["echo", "hi"]
    return r


def _next(result):
    return result


class TestTracingMiddlewareSuccess:
    def test_delegates_to_next(self):
        mw = TracingMiddleware()
        r = _result()
        out = mw(r, _next)
        assert out is r

    def test_records_one_span(self):
        mw = TracingMiddleware()
        mw(_result(), _next)
        assert len(mw.tracer.spans) == 1

    def test_span_is_finished(self):
        mw = TracingMiddleware()
        mw(_result(), _next)
        assert mw.tracer.spans[0].end_time is not None

    def test_span_has_exit_code(self):
        mw = TracingMiddleware()
        mw(_result(exit_code=2), _next)
        assert mw.tracer.spans[0].attributes["exit_code"] == 2

    def test_span_has_success_true_on_zero(self):
        mw = TracingMiddleware()
        mw(_result(exit_code=0), _next)
        assert mw.tracer.spans[0].attributes["success"] is True

    def test_span_has_success_false_on_nonzero(self):
        mw = TracingMiddleware()
        mw(_result(exit_code=1), _next)
        assert mw.tracer.spans[0].attributes["success"] is False

    def test_span_stores_attempt_number(self):
        mw = TracingMiddleware()
        mw(_result(attempts=3), _next)
        assert mw.tracer.spans[0].attributes["attempt"] == 3

    def test_accepts_custom_tracer(self):
        tracer = Tracer(trace_id="custom")
        mw = TracingMiddleware(tracer=tracer)
        assert mw.tracer.trace_id == "custom"

    def test_reset_clears_spans(self):
        mw = TracingMiddleware()
        mw(_result(), _next)
        mw.reset()
        assert mw.tracer.spans == []

    def test_exception_finishes_span(self):
        mw = TracingMiddleware()

        def boom(r):
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            mw(_result(), boom)
        assert mw.tracer.spans[0].end_time is not None
        assert "error" in mw.tracer.spans[0].attributes

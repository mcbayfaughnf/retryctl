"""Tests for retryctl.tee."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from retryctl.runner import CommandResult
from retryctl.tee import TeeError, TeeMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0) -> CommandResult:
    return CommandResult(command="echo hi", exit_code=exit_code, stdout="hi", stderr="", attempts=1, elapsed=0.1)


def _next(result: CommandResult) -> CommandResult:
    """Identity next() callable."""
    return result


# ---------------------------------------------------------------------------
# TeeMiddlewareInit
# ---------------------------------------------------------------------------

class TestTeeMiddlewareInit:
    def test_default_no_sinks(self):
        tee = TeeMiddleware()
        assert tee.sink_count == 0

    def test_sinks_from_constructor(self):
        sink = MagicMock()
        tee = TeeMiddleware(sinks=[sink])
        assert tee.sink_count == 1

    def test_strict_defaults_to_false(self):
        tee = TeeMiddleware()
        assert tee.strict is False


# ---------------------------------------------------------------------------
# TeeMiddlewareSinkManagement
# ---------------------------------------------------------------------------

class TestTeeMiddlewareSinkManagement:
    def test_add_sink_increments_count(self):
        tee = TeeMiddleware()
        tee.add_sink(MagicMock())
        assert tee.sink_count == 1

    def test_add_same_sink_twice_is_idempotent(self):
        tee = TeeMiddleware()
        sink = MagicMock()
        tee.add_sink(sink)
        tee.add_sink(sink)
        assert tee.sink_count == 1

    def test_remove_sink_decrements_count(self):
        tee = TeeMiddleware()
        sink = MagicMock()
        tee.add_sink(sink)
        tee.remove_sink(sink)
        assert tee.sink_count == 0

    def test_remove_unknown_sink_is_noop(self):
        tee = TeeMiddleware()
        tee.remove_sink(MagicMock())  # should not raise

    def test_reset_clears_all_sinks(self):
        tee = TeeMiddleware(sinks=[MagicMock(), MagicMock()])
        tee.reset()
        assert tee.sink_count == 0


# ---------------------------------------------------------------------------
# TeeMiddlewareCall
# ---------------------------------------------------------------------------

class TestTeeMiddlewareCall:
    def test_delegates_to_next(self):
        tee = TeeMiddleware()
        r = _result()
        outcome = tee(r, _next)
        assert outcome is r

    def test_calls_each_sink_with_result(self):
        sink1, sink2 = MagicMock(), MagicMock()
        tee = TeeMiddleware(sinks=[sink1, sink2])
        r = _result()
        tee(r, _next)
        sink1.assert_called_once_with(r)
        sink2.assert_called_once_with(r)

    def test_sink_receives_next_output_not_input(self):
        """Sink should see the result returned by next(), not the raw input."""
        transformed = _result(exit_code=42)

        def _transforming_next(_r: CommandResult) -> CommandResult:
            return transformed

        sink = MagicMock()
        tee = TeeMiddleware(sinks=[sink])
        tee(_result(exit_code=0), _transforming_next)
        sink.assert_called_once_with(transformed)

    def test_lax_mode_swallows_sink_error(self):
        bad_sink = MagicMock(side_effect=RuntimeError("boom"))
        tee = TeeMiddleware(sinks=[bad_sink], strict=False)
        r = _result()
        outcome = tee(r, _next)  # should not raise
        assert outcome is r

    def test_strict_mode_raises_tee_error_on_sink_failure(self):
        bad_sink = MagicMock(side_effect=RuntimeError("boom"))
        tee = TeeMiddleware(sinks=[bad_sink], strict=True)
        with pytest.raises(TeeError) as exc_info:
            tee(_result(), _next)
        assert exc_info.value.sink is bad_sink
        assert isinstance(exc_info.value.cause, RuntimeError)

    def test_strict_good_sinks_still_called_before_bad_one(self):
        good = MagicMock()
        bad = MagicMock(side_effect=RuntimeError("oops"))
        tee = TeeMiddleware(sinks=[good, bad], strict=True)
        with pytest.raises(TeeError):
            tee(_result(), _next)
        good.assert_called_once()

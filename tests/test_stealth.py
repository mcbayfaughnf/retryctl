"""Tests for retryctl.stealth."""
from __future__ import annotations

import pytest

from retryctl.runner import CommandResult
from retryctl.stealth import StealthBuffer, StealthConfig, StealthMiddleware


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(
        command="echo hi",
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        attempts=1,
        elapsed=0.01,
    )


def _next(result: CommandResult):
    """Return a callable that always yields *result*."""
    def _fn(*_a, **_kw):
        return result
    return _fn


# ---------------------------------------------------------------------------
# StealthConfig
# ---------------------------------------------------------------------------

class TestStealthConfig:
    def test_defaults_are_truthy(self):
        cfg = StealthConfig()
        assert cfg.suppress_stdout is True
        assert cfg.suppress_stderr is True
        assert cfg.release_on_failure is True

    def test_both_false_raises(self):
        with pytest.raises(ValueError, match="at least one"):
            StealthConfig(suppress_stdout=False, suppress_stderr=False)

    def test_one_true_is_valid(self):
        cfg = StealthConfig(suppress_stdout=True, suppress_stderr=False)
        assert cfg.suppress_stdout is True


# ---------------------------------------------------------------------------
# StealthBuffer
# ---------------------------------------------------------------------------

class TestStealthBuffer:
    def test_record_accumulates_stdout(self):
        buf = StealthBuffer()
        buf.record(_result(stdout="hello\n"))
        assert buf.stdout_captured == "hello\n"

    def test_record_accumulates_stderr(self):
        buf = StealthBuffer()
        buf.record(_result(stderr="err\n"))
        assert buf.stderr_captured == "err\n"

    def test_clear_empties_buffers(self):
        buf = StealthBuffer()
        buf.record(_result(stdout="data", stderr="noise"))
        buf.clear()
        assert buf.stdout_captured == ""
        assert buf.stderr_captured == ""

    def test_release_writes_to_streams(self, capsys):
        buf = StealthBuffer()
        buf.record(_result(stdout="out\n", stderr="err\n"))
        buf.release()
        captured = capsys.readouterr()
        assert "out" in captured.out
        assert "err" in captured.err


# ---------------------------------------------------------------------------
# StealthMiddleware
# ---------------------------------------------------------------------------

class TestStealthMiddlewareSuccess:
    def test_delegates_to_next(self):
        mw = StealthMiddleware()
        res = _result(exit_code=0, stdout="quiet\n")
        returned = mw(_next(res))
        assert returned.exit_code == 0

    def test_buffer_cleared_on_success(self):
        mw = StealthMiddleware()
        mw(_next(_result(exit_code=0, stdout="shh")))
        assert mw.buffer.stdout_captured == ""

    def test_output_not_printed_on_success(self, capsys):
        mw = StealthMiddleware()
        mw(_next(_result(exit_code=0, stdout="secret\n")))
        assert capsys.readouterr().out == ""


class TestStealthMiddlewareFailure:
    def test_buffer_cleared_after_release_on_failure(self):
        mw = StealthMiddleware(StealthConfig(release_on_failure=True))
        mw(_next(_result(exit_code=1, stdout="noise")))
        assert mw.buffer.stdout_captured == ""

    def test_output_released_on_failure(self, capsys):
        mw = StealthMiddleware(StealthConfig(release_on_failure=True))
        mw(_next(_result(exit_code=1, stdout="visible\n")))
        assert "visible" in capsys.readouterr().out

    def test_output_suppressed_when_release_off(self, capsys):
        mw = StealthMiddleware(StealthConfig(release_on_failure=False))
        mw(_next(_result(exit_code=1, stdout="hidden\n")))
        assert capsys.readouterr().out == ""


class TestStealthMiddlewareReset:
    def test_reset_clears_buffer(self):
        mw = StealthMiddleware()
        mw.buffer.record(_result(stdout="leftover"))
        mw.reset()
        assert mw.buffer.stdout_captured == ""

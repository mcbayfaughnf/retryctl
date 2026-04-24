"""Tests for retryctl.fallback."""
from __future__ import annotations

import pytest

from retryctl.fallback import (
    FallbackError,
    FallbackMiddleware,
    FallbackPolicy,
    FallbackResult,
)
from retryctl.runner import CommandResult


def _result(exit_code: int = 0, stdout: str = "") -> CommandResult:
    return CommandResult(
        command=["cmd"],
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
        attempts=1,
    )


def _next(result: CommandResult):
    def _fn(cmd):
        return result

    return _fn


def _fb_runner(result: CommandResult):
    def _fn(cmd):
        return result

    return _fn


# ---------------------------------------------------------------------------
# FallbackPolicy
# ---------------------------------------------------------------------------

class TestFallbackPolicyInit:
    def test_valid_any_failure(self):
        p = FallbackPolicy(command=["echo", "fallback"], on_any_failure=True)
        assert p.on_any_failure is True

    def test_valid_exit_codes(self):
        p = FallbackPolicy(command=["echo"], on_exit_codes=[1, 2])
        assert 1 in p.on_exit_codes

    def test_empty_command_raises(self):
        with pytest.raises(FallbackError, match="empty"):
            FallbackPolicy(command=[], on_any_failure=True)

    def test_no_trigger_condition_raises(self):
        with pytest.raises(FallbackError, match="requires"):
            FallbackPolicy(command=["echo"])


class TestFallbackPolicyShouldFallback:
    def test_success_does_not_trigger(self):
        p = FallbackPolicy(command=["echo"], on_any_failure=True)
        assert p.should_fallback(_result(0)) is False

    def test_any_failure_triggers_on_nonzero(self):
        p = FallbackPolicy(command=["echo"], on_any_failure=True)
        assert p.should_fallback(_result(1)) is True

    def test_exit_code_match_triggers(self):
        p = FallbackPolicy(command=["echo"], on_exit_codes=[2])
        assert p.should_fallback(_result(2)) is True

    def test_exit_code_no_match_does_not_trigger(self):
        p = FallbackPolicy(command=["echo"], on_exit_codes=[2])
        assert p.should_fallback(_result(3)) is False


# ---------------------------------------------------------------------------
# FallbackMiddleware
# ---------------------------------------------------------------------------

class TestFallbackMiddlewareSuccess:
    def test_delegates_to_next_on_success(self):
        policy = FallbackPolicy(command=["fb"], on_any_failure=True)
        mw = FallbackMiddleware(policy)
        r = _result(0, "ok")
        out = mw(["cmd"], _next(r))
        assert out.exit_code == 0

    def test_no_fallback_triggered_on_success(self):
        policy = FallbackPolicy(command=["fb"], on_any_failure=True)
        mw = FallbackMiddleware(policy)
        mw(["cmd"], _next(_result(0)))
        assert mw.last_fallback is not None
        assert mw.last_fallback.triggered is False

    def test_fallback_called_on_failure(self):
        policy = FallbackPolicy(command=["fb"], on_any_failure=True)
        fb_res = _result(0, "fallback output")
        mw = FallbackMiddleware(policy, runner=_fb_runner(fb_res))
        out = mw(["cmd"], _next(_result(1)))
        assert out.stdout == "fallback output"

    def test_last_fallback_stores_original(self):
        policy = FallbackPolicy(command=["fb"], on_any_failure=True)
        original = _result(1)
        fb_res = _result(0)
        mw = FallbackMiddleware(policy, runner=_fb_runner(fb_res))
        mw(["cmd"], _next(original))
        assert mw.last_fallback.original.exit_code == 1

    def test_reset_clears_last_fallback(self):
        policy = FallbackPolicy(command=["fb"], on_any_failure=True)
        mw = FallbackMiddleware(policy, runner=_fb_runner(_result(0)))
        mw(["cmd"], _next(_result(1)))
        mw.reset()
        assert mw.last_fallback is None

"""Tests for retryctl.pause and retryctl.pause_middleware."""
from __future__ import annotations

import threading
import time

import pytest

from retryctl.pause import (
    PauseController,
    PausePolicy,
    PauseTimeout,
)
from retryctl.pause_middleware import PauseMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0) -> CommandResult:
    return CommandResult(command="echo hi", exit_code=exit_code, stdout="", stderr="", attempts=1)


def _next(result: CommandResult):
    def fn(*_args, **_kwargs):
        return result
    return fn


# ---------------------------------------------------------------------------
# PausePolicy
# ---------------------------------------------------------------------------

class TestPausePolicyInit:
    def test_valid_defaults(self):
        p = PausePolicy()
        assert p.max_wait == 0.0
        assert p.poll_interval == 0.05

    def test_negative_max_wait_raises(self):
        with pytest.raises(ValueError, match="max_wait"):
            PausePolicy(max_wait=-1.0)

    def test_zero_poll_interval_raises(self):
        with pytest.raises(ValueError, match="poll_interval"):
            PausePolicy(poll_interval=0.0)

    def test_negative_poll_interval_raises(self):
        with pytest.raises(ValueError, match="poll_interval"):
            PausePolicy(poll_interval=-0.1)


# ---------------------------------------------------------------------------
# PauseController
# ---------------------------------------------------------------------------

class TestPauseController:
    def test_not_paused_initially(self):
        ctrl = PauseController()
        assert not ctrl.is_paused

    def test_pause_sets_paused(self):
        ctrl = PauseController()
        ctrl.pause()
        assert ctrl.is_paused

    def test_resume_clears_paused(self):
        ctrl = PauseController()
        ctrl.pause()
        ctrl.resume()
        assert not ctrl.is_paused

    def test_wait_returns_zero_when_not_paused(self):
        ctrl = PauseController()
        waited = ctrl.wait_if_paused()
        assert waited == 0.0

    def test_wait_blocks_until_resumed(self):
        ctrl = PauseController(PausePolicy(poll_interval=0.01))
        ctrl.pause()

        def _resume_after():
            time.sleep(0.05)
            ctrl.resume()

        t = threading.Thread(target=_resume_after, daemon=True)
        t.start()
        waited = ctrl.wait_if_paused()
        t.join(timeout=1)
        assert waited >= 0.04

    def test_max_wait_raises_pause_timeout(self):
        policy = PausePolicy(max_wait=0.05, poll_interval=0.01)
        ctrl = PauseController(policy)
        ctrl.pause()
        with pytest.raises(PauseTimeout) as exc_info:
            ctrl.wait_if_paused()
        assert exc_info.value.limit == 0.05

    def test_double_pause_is_idempotent(self):
        ctrl = PauseController()
        ctrl.pause()
        ctrl.pause()  # should not raise
        assert ctrl.is_paused


# ---------------------------------------------------------------------------
# PauseTimeout
# ---------------------------------------------------------------------------

class TestPauseTimeout:
    def test_stores_waited_and_limit(self):
        exc = PauseTimeout(waited=3.0, limit=2.0)
        assert exc.waited == 3.0
        assert exc.limit == 2.0

    def test_message_contains_values(self):
        exc = PauseTimeout(waited=3.0, limit=2.0)
        assert "3.00" in str(exc)
        assert "2.00" in str(exc)


# ---------------------------------------------------------------------------
# PauseMiddleware
# ---------------------------------------------------------------------------

class TestPauseMiddleware:
    def test_delegates_to_next_when_not_paused(self):
        mw = PauseMiddleware()
        result = _result(exit_code=0)
        out = mw(_next(result))
        assert out is result

    def test_exposes_controller(self):
        mw = PauseMiddleware()
        assert isinstance(mw.controller, PauseController)

    def test_accepts_external_controller(self):
        ctrl = PauseController()
        mw = PauseMiddleware(controller=ctrl)
        assert mw.controller is ctrl

    def test_pause_resume_via_middleware(self):
        mw = PauseMiddleware(PauseController(PausePolicy(poll_interval=0.01)))
        mw.pause()

        def _resume():
            time.sleep(0.05)
            mw.resume()

        t = threading.Thread(target=_resume, daemon=True)
        t.start()
        result = _result()
        out = mw(_next(result))
        t.join(timeout=1)
        assert out is result

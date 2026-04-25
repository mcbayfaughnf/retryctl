"""Tests for retryctl.scatter."""
from __future__ import annotations

import pytest

from retryctl.runner import CommandResult
from retryctl.scatter import (
    ScatterError,
    ScatterMiddleware,
    ScatterPolicy,
    ScatterResult,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0, stdout: str = "ok") -> CommandResult:
    return CommandResult(
        command=["echo", stdout],
        exit_code=exit_code,
        stdout=stdout,
        stderr="",
        attempts=1,
        elapsed=0.01,
    )


def _next(exit_code: int = 0):
    """Return a callable that always produces a result with *exit_code*."""
    def _fn(*args, **kwargs):
        return _result(exit_code=exit_code)
    return _fn


# ---------------------------------------------------------------------------
# ScatterPolicy
# ---------------------------------------------------------------------------

class TestScatterPolicyInit:
    def test_valid_defaults(self):
        p = ScatterPolicy()
        assert p.lanes == 3
        assert p.quorum == 2

    def test_zero_lanes_raises(self):
        with pytest.raises(ValueError, match="lanes"):
            ScatterPolicy(lanes=0)

    def test_quorum_exceeds_lanes_raises(self):
        with pytest.raises(ValueError, match="quorum cannot exceed"):
            ScatterPolicy(lanes=2, quorum=3)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout"):
            ScatterPolicy(timeout=-1.0)

    def test_zero_quorum_raises(self):
        with pytest.raises(ValueError, match="quorum"):
            ScatterPolicy(quorum=0)


# ---------------------------------------------------------------------------
# ScatterResult
# ---------------------------------------------------------------------------

class TestScatterResult:
    def test_best_returns_first_success(self):
        sr = ScatterResult(
            results=[_result(1), _result(0), _result(0)],
            succeeded=2,
            failed=1,
        )
        assert sr.best is not None
        assert sr.best.exit_code == 0

    def test_best_falls_back_to_first_on_all_failure(self):
        r = _result(1)
        sr = ScatterResult(results=[r], succeeded=0, failed=1)
        assert sr.best is r

    def test_best_none_when_empty(self):
        assert ScatterResult().best is None


# ---------------------------------------------------------------------------
# ScatterMiddleware – success paths
# ---------------------------------------------------------------------------

class TestScatterMiddlewareSuccess:
    def test_delegates_to_next(self):
        mw = ScatterMiddleware(ScatterPolicy(lanes=3, quorum=2))
        result = mw(_next(exit_code=0))
        assert result.exit_code == 0

    def test_quorum_met_returns_result(self):
        mw = ScatterMiddleware(ScatterPolicy(lanes=5, quorum=3))
        result = mw(_next(exit_code=0))
        assert result is not None

    def test_policy_property(self):
        p = ScatterPolicy(lanes=2, quorum=1)
        mw = ScatterMiddleware(p)
        assert mw.policy is p


# ---------------------------------------------------------------------------
# ScatterMiddleware – failure paths
# ---------------------------------------------------------------------------

class TestScatterMiddlewareFailure:
    def test_raises_scatter_error_when_quorum_not_met(self):
        mw = ScatterMiddleware(ScatterPolicy(lanes=3, quorum=2))
        with pytest.raises(ScatterError) as exc_info:
            mw(_next(exit_code=1))
        err = exc_info.value
        assert err.succeeded == 0
        assert err.quorum == 2
        assert err.total == 3

    def test_scatter_error_message(self):
        err = ScatterError(succeeded=1, quorum=3, total=4)
        assert "1/4" in str(err)
        assert "3" in str(err)

    def test_default_policy_used_when_none_given(self):
        mw = ScatterMiddleware()
        assert mw.policy.lanes == 3
        assert mw.policy.quorum == 2

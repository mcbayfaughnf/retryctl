"""Tests for retryctl.deadline and retryctl.deadline_middleware."""
from __future__ import annotations

import time
import pytest

from retryctl.deadline import Deadline, DeadlineExceeded, maybe_deadline
from retryctl.deadline_middleware import DeadlineMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(code: int = 0) -> CommandResult:
    return CommandResult(command="echo hi", exit_code=code, stdout="", stderr="", attempts=1)


# ---------------------------------------------------------------------------
# Deadline
# ---------------------------------------------------------------------------

class TestDeadlineInit:
    def test_zero_limit_raises(self):
        with pytest.raises(ValueError):
            Deadline(limit=0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError):
            Deadline(limit=-1)

    def test_not_expired_immediately(self):
        d = Deadline(limit=60)
        assert not d.expired

    def test_remaining_close_to_limit_initially(self):
        d = Deadline(limit=10)
        assert d.remaining > 9.9

    def test_check_does_not_raise_when_fresh(self):
        d = Deadline(limit=60)
        d.check()  # should not raise

    def test_expired_after_limit(self):
        d = Deadline(limit=0.05)
        time.sleep(0.1)
        assert d.expired

    def test_check_raises_after_limit(self):
        d = Deadline(limit=0.05)
        time.sleep(0.1)
        with pytest.raises(DeadlineExceeded):
            d.check()

    def test_exceeded_message_contains_limit(self):
        exc = DeadlineExceeded(deadline=5.0, now=6.0)
        assert "5.00" in str(exc)

    def test_exceeded_stores_fields(self):
        exc = DeadlineExceeded(deadline=3.0, now=4.5)
        assert exc.deadline == 3.0
        assert exc.now == 4.5


class TestMaybeDeadline:
    def test_none_returns_none(self):
        assert maybe_deadline(None) is None

    def test_value_returns_deadline(self):
        d = maybe_deadline(30.0)
        assert isinstance(d, Deadline)


# ---------------------------------------------------------------------------
# DeadlineMiddleware
# ---------------------------------------------------------------------------

class TestDeadlineMiddlewareNoLimit:
    def test_delegates_to_next(self):
        mw = DeadlineMiddleware()
        result = mw(lambda: _result(0))
        assert result.exit_code == 0

    def test_remaining_is_none(self):
        mw = DeadlineMiddleware()
        assert mw.remaining is None

    def test_expired_is_false(self):
        mw = DeadlineMiddleware()
        assert mw.expired is False


class TestDeadlineMiddlewareWithLimit:
    def test_delegates_when_within_limit(self):
        mw = DeadlineMiddleware(limit=60)
        result = mw(lambda: _result(0))
        assert result.exit_code == 0

    def test_raises_when_expired(self):
        d = Deadline(limit=0.05)
        time.sleep(0.1)
        mw = DeadlineMiddleware(_deadline=d)
        with pytest.raises(DeadlineExceeded):
            mw(lambda: _result(0))

    def test_remaining_decreases(self):
        mw = DeadlineMiddleware(limit=10)
        r1 = mw.remaining
        time.sleep(0.05)
        r2 = mw.remaining
        assert r2 < r1

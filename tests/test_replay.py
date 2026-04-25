"""Tests for retryctl.replay."""
from __future__ import annotations

import pytest

from retryctl.replay import ReplayError, ReplayMiddleware, ReplayStore
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0, stdout: str = "ok", stderr: str = "") -> CommandResult:
    return CommandResult(
        command=["echo", "hi"],
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        attempts=1,
        elapsed=0.1,
    )


def _next(result: CommandResult):
    def _fn(*args, **kwargs):
        return result
    return _fn


# ---------------------------------------------------------------------------
# ReplayStore
# ---------------------------------------------------------------------------

class TestReplayStoreInit:
    def test_default_max_size(self):
        s = ReplayStore()
        assert s.max_size == 10

    def test_custom_max_size(self):
        s = ReplayStore(max_size=3)
        assert s.max_size == 3

    def test_zero_max_size_raises(self):
        with pytest.raises(ValueError):
            ReplayStore(max_size=0)

    def test_negative_max_size_raises(self):
        with pytest.raises(ValueError):
            ReplayStore(max_size=-1)


class TestReplayStoreRecord:
    def test_size_increments(self):
        s = ReplayStore()
        s.record(_result())
        assert s.size == 1

    def test_evicts_oldest_when_full(self):
        s = ReplayStore(max_size=2)
        r1, r2, r3 = _result(stdout="a"), _result(stdout="b"), _result(stdout="c")
        s.record(r1)
        s.record(r2)
        s.record(r3)
        assert s.size == 2
        assert s.latest() is r3

    def test_clear_empties_store(self):
        s = ReplayStore()
        s.record(_result())
        s.clear()
        assert s.size == 0


class TestReplayStoreLatest:
    def test_raises_when_empty(self):
        s = ReplayStore()
        with pytest.raises(ReplayError):
            s.latest()

    def test_returns_most_recent(self):
        s = ReplayStore()
        r1, r2 = _result(stdout="first"), _result(stdout="second")
        s.record(r1)
        s.record(r2)
        assert s.latest() is r2


# ---------------------------------------------------------------------------
# ReplayMiddleware
# ---------------------------------------------------------------------------

class TestReplayMiddlewareNormalMode:
    def test_delegates_to_next(self):
        r = _result()
        mw = ReplayMiddleware()
        assert mw(_next(r)) is r

    def test_records_successful_result(self):
        r = _result(exit_code=0)
        mw = ReplayMiddleware()
        mw(_next(r))
        assert mw.store.size == 1

    def test_does_not_record_failed_result(self):
        r = _result(exit_code=1)
        mw = ReplayMiddleware()
        mw(_next(r))
        assert mw.store.size == 0

    def test_record_successes_false_skips_recording(self):
        r = _result(exit_code=0)
        mw = ReplayMiddleware(record_successes=False)
        mw(_next(r))
        assert mw.store.size == 0


class TestReplayMiddlewareReplayMode:
    def test_returns_stored_result_without_calling_next(self):
        stored = _result(stdout="stored")
        store = ReplayStore()
        store.record(stored)

        called = []
        def next_fn(*a, **kw):
            called.append(True)
            return _result(stdout="live")

        mw = ReplayMiddleware(store=store, replay=True)
        result = mw(next_fn)
        assert result is stored
        assert not called

    def test_raises_when_no_history(self):
        mw = ReplayMiddleware(replay=True)
        with pytest.raises(ReplayError):
            mw(_next(_result()))

    def test_enable_disable_replay(self):
        mw = ReplayMiddleware()
        assert not mw.replaying
        mw.enable_replay()
        assert mw.replaying
        mw.disable_replay()
        assert not mw.replaying

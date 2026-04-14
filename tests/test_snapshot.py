"""Tests for retryctl.snapshot and retryctl.snapshot_middleware."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from retryctl.runner import CommandResult
from retryctl.snapshot import OutputSnapshot, SnapshotHistory
from retryctl.snapshot_middleware import SnapshotMiddleware


def _snap(attempt=1, stdout="out", stderr="err", exit_code=0):
    return OutputSnapshot(attempt=attempt, stdout=stdout, stderr=stderr, exit_code=exit_code)


def _result(stdout="out", stderr="err", exit_code=0):
    r = MagicMock(spec=CommandResult)
    r.stdout = stdout
    r.stderr = stderr
    r.exit_code = exit_code
    return r


# ---------------------------------------------------------------------------
# OutputSnapshot
# ---------------------------------------------------------------------------

class TestOutputSnapshot:
    def test_digest_is_sha256_hex(self):
        snap = _snap()
        assert len(snap.digest) == 64
        assert all(c in "0123456789abcdef" for c in snap.digest)

    def test_identical_snapshots_match(self):
        a, b = _snap(), _snap()
        assert a.matches(b)

    def test_different_stdout_does_not_match(self):
        a = _snap(stdout="hello")
        b = _snap(stdout="world")
        assert not a.matches(b)

    def test_different_exit_code_does_not_match(self):
        a = _snap(exit_code=0)
        b = _snap(exit_code=1)
        assert not a.matches(b)


# ---------------------------------------------------------------------------
# SnapshotHistory
# ---------------------------------------------------------------------------

class TestSnapshotHistory:
    def test_empty_latest_is_none(self):
        assert SnapshotHistory().latest() is None

    def test_empty_previous_is_none(self):
        assert SnapshotHistory().previous() is None

    def test_record_increases_length(self):
        h = SnapshotHistory()
        h.record(_snap(attempt=1))
        h.record(_snap(attempt=2))
        assert len(h) == 2

    def test_output_changed_false_when_same(self):
        h = SnapshotHistory()
        h.record(_snap(stdout="x"))
        h.record(_snap(stdout="x"))
        assert not h.output_changed()

    def test_output_changed_true_when_different(self):
        h = SnapshotHistory()
        h.record(_snap(stdout="x"))
        h.record(_snap(stdout="y"))
        assert h.output_changed()

    def test_output_changed_false_with_single_entry(self):
        h = SnapshotHistory()
        h.record(_snap())
        assert not h.output_changed()


# ---------------------------------------------------------------------------
# SnapshotMiddleware
# ---------------------------------------------------------------------------

class TestSnapshotMiddleware:
    def test_delegates_to_next(self):
        expected = _result()
        next_fn = MagicMock(return_value=expected)
        mw = SnapshotMiddleware(next_fn)
        assert mw(attempt=1) is expected

    def test_records_snapshot_after_call(self):
        mw = SnapshotMiddleware(MagicMock(return_value=_result(stdout="hi")))
        mw(attempt=1)
        assert len(mw.history) == 1
        assert mw.history.latest().stdout == "hi"

    def test_on_change_called_when_output_differs(self):
        results = [_result(stdout="a"), _result(stdout="b")]
        idx = iter(results)
        next_fn = MagicMock(side_effect=lambda **kw: next(idx))
        callback = MagicMock()
        mw = SnapshotMiddleware(next_fn, on_change=callback)
        mw(attempt=1)
        mw(attempt=2)
        callback.assert_called_once()

    def test_on_change_not_called_when_output_same(self):
        next_fn = MagicMock(return_value=_result(stdout="same"))
        callback = MagicMock()
        mw = SnapshotMiddleware(next_fn, on_change=callback)
        mw(attempt=1)
        mw(attempt=2)
        callback.assert_not_called()

    def test_reset_clears_history(self):
        mw = SnapshotMiddleware(MagicMock(return_value=_result()))
        mw(attempt=1)
        mw.reset()
        assert len(mw.history) == 0

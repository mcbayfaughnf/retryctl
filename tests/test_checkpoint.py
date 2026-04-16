"""Tests for checkpoint.py and checkpoint_middleware.py."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from retryctl.checkpoint import CheckpointData, CheckpointStore
from retryctl.checkpoint_middleware import CheckpointMiddleware
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _store(tmp_path: Path) -> CheckpointStore:
    return CheckpointStore(tmp_path / "cp.json")


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    return r


# ---------------------------------------------------------------------------
# CheckpointData
# ---------------------------------------------------------------------------

class TestCheckpointData:
    def test_round_trip(self):
        d = CheckpointData(command="echo hi", attempt=3, last_exit_code=1)
        restored = CheckpointData.from_dict(d.to_dict())
        assert restored.command == "echo hi"
        assert restored.attempt == 3
        assert restored.last_exit_code == 1

    def test_updated_at_changes_on_save(self, tmp_path):
        store = _store(tmp_path)
        d = CheckpointData(command="x", attempt=1, last_exit_code=None)
        old_ts = d.updated_at
        time.sleep(0.01)
        store.save(d)
        loaded = store.load()
        assert loaded.updated_at >= old_ts


# ---------------------------------------------------------------------------
# CheckpointStore
# ---------------------------------------------------------------------------

class TestCheckpointStore:
    def test_load_returns_none_when_missing(self, tmp_path):
        assert _store(tmp_path).load() is None

    def test_save_and_load(self, tmp_path):
        store = _store(tmp_path)
        store.save(CheckpointData(command="ls", attempt=2, last_exit_code=1))
        data = store.load()
        assert data is not None
        assert data.attempt == 2
        assert data.command == "ls"

    def test_clear_removes_file(self, tmp_path):
        store = _store(tmp_path)
        store.save(CheckpointData(command="ls", attempt=1, last_exit_code=1))
        store.clear()
        assert not store.exists

    def test_load_returns_none_on_corrupt_file(self, tmp_path):
        p = tmp_path / "cp.json"
        p.write_text("not-json")
        assert CheckpointStore(p).load() is None


# ---------------------------------------------------------------------------
# CheckpointMiddleware
# ---------------------------------------------------------------------------

class TestCheckpointMiddleware:
    def test_resume_from_defaults_to_1(self, tmp_path):
        mw = CheckpointMiddleware(_store(tmp_path), "cmd")
        assert mw.resume_from == 1

    def test_resume_from_reflects_saved_checkpoint(self, tmp_path):
        store = _store(tmp_path)
        store.save(CheckpointData(command="cmd", attempt=4, last_exit_code=1))
        mw = CheckpointMiddleware(store, "cmd")
        assert mw.resume_from == 4

    def test_clears_checkpoint_on_success(self, tmp_path):
        store = _store(tmp_path)
        store.save(CheckpointData(command="cmd", attempt=2, last_exit_code=1))
        mw = CheckpointMiddleware(store, "cmd")
        mw(lambda *a, **kw: _result(0), attempt=3)
        assert not store.exists

    def test_saves_checkpoint_on_failure(self, tmp_path):
        store = _store(tmp_path)
        mw = CheckpointMiddleware(store, "cmd")
        mw(lambda *a, **kw: _result(2), attempt=2)
        data = store.load()
        assert data is not None
        assert data.last_exit_code == 2

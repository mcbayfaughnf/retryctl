"""Tests for retryctl.audit."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from retryctl.audit import AuditEntry, AuditLogger, build_entry
from retryctl.reporter import AttemptRecord, RunSummary
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_result(cmd=("echo", "hi"), exit_code=0, stdout="hi", stderr=""):
    r = MagicMock(spec=CommandResult)
    r.command = list(cmd)
    r.exit_code = exit_code
    r.stdout = stdout
    r.stderr = stderr
    return r


def _make_summary(succeeded=True, n_attempts=1):
    result = _make_result(exit_code=0 if succeeded else 1)
    attempts = [
        AttemptRecord(attempt=i + 1, result=result, duration=0.1)
        for i in range(n_attempts)
    ]
    summary = MagicMock(spec=RunSummary)
    summary.attempts = attempts
    summary.succeeded = succeeded
    summary.total_duration = 0.1 * n_attempts
    return summary


# ---------------------------------------------------------------------------
# AuditEntry
# ---------------------------------------------------------------------------

class TestAuditEntry:
    def test_to_json_is_valid(self):
        entry = AuditEntry(
            timestamp="2024-01-01T00:00:00+00:00",
            command=["echo", "hi"],
            exit_code=0,
            attempts=1,
            total_duration=0.05,
            succeeded=True,
        )
        parsed = json.loads(entry.to_json())
        assert parsed["exit_code"] == 0
        assert parsed["command"] == ["echo", "hi"]

    def test_extra_defaults_to_empty_dict(self):
        entry = AuditEntry(
            timestamp="t", command=[], exit_code=0,
            attempts=1, total_duration=0.0, succeeded=True,
        )
        assert entry.extra == {}


# ---------------------------------------------------------------------------
# build_entry
# ---------------------------------------------------------------------------

class TestBuildEntry:
    def test_exit_code_from_last_attempt(self):
        summary = _make_summary(succeeded=False, n_attempts=3)
        entry = build_entry(summary)
        assert entry.exit_code == 1

    def test_attempts_count(self):
        summary = _make_summary(n_attempts=4)
        entry = build_entry(summary)
        assert entry.attempts == 4

    def test_extra_forwarded(self):
        summary = _make_summary()
        entry = build_entry(summary, extra={"env": "ci"})
        assert entry.extra["env"] == "ci"

    def test_empty_attempts_gives_minus_one(self):
        summary = MagicMock(spec=RunSummary)
        summary.attempts = []
        summary.succeeded = False
        summary.total_duration = 0.0
        entry = build_entry(summary)
        assert entry.exit_code == -1


# ---------------------------------------------------------------------------
# AuditLogger
# ---------------------------------------------------------------------------

class TestAuditLogger:
    def test_creates_parent_dirs(self, tmp_path):
        log_file = tmp_path / "nested" / "dir" / "audit.jsonl"
        logger = AuditLogger(log_file)
        assert logger.path.parent.exists()

    def test_write_appends_jsonl(self, tmp_path):
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file)
        entry = AuditEntry(
            timestamp="t", command=["ls"], exit_code=0,
            attempts=1, total_duration=0.01, succeeded=True,
        )
        logger.write(entry)
        logger.write(entry)
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["exit_code"] == 0

    def test_log_summary_returns_entry(self, tmp_path):
        logger = AuditLogger(tmp_path / "audit.jsonl")
        summary = _make_summary(n_attempts=2)
        entry = logger.log_summary(summary)
        assert entry.attempts == 2
        assert entry.log_path != ""

    def test_log_path_recorded_in_entry(self, tmp_path):
        log_file = tmp_path / "audit.jsonl"
        logger = AuditLogger(log_file)
        summary = _make_summary()
        entry = logger.log_summary(summary)
        assert entry.log_path == str(log_file)

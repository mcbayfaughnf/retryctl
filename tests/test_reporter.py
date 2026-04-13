"""Tests for retryctl.reporter."""

from __future__ import annotations

import pytest

from retryctl.reporter import AttemptRecord, RunSummary
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(exit_code: int = 0, attempts: int = 1, stderr: str = "") -> CommandResult:
    return CommandResult(
        command=["echo", "hi"],
        exit_code=exit_code,
        stdout="out",
        stderr=stderr,
        attempts=attempts,
    )


def _make_summary() -> RunSummary:
    return RunSummary(command=["echo", "hi"])


# ---------------------------------------------------------------------------
# AttemptRecord
# ---------------------------------------------------------------------------

class TestAttemptRecord:
    def test_stores_fields(self):
        rec = AttemptRecord(attempt=1, exit_code=0, duration=0.5)
        assert rec.attempt == 1
        assert rec.exit_code == 0
        assert rec.duration == 0.5
        assert rec.error is None

    def test_stores_error(self):
        rec = AttemptRecord(attempt=2, exit_code=1, duration=0.1, error="oops")
        assert rec.error == "oops"


# ---------------------------------------------------------------------------
# RunSummary.record_attempt
# ---------------------------------------------------------------------------

class TestRunSummaryRecordAttempt:
    def test_appends_record(self):
        summary = _make_summary()
        summary.record_attempt(_make_result(exit_code=1, attempts=1), duration=0.2)
        assert len(summary.attempts) == 1

    def test_exit_code_stored(self):
        summary = _make_summary()
        summary.record_attempt(_make_result(exit_code=42, attempts=1), duration=0.1)
        assert summary.attempts[0].exit_code == 42

    def test_stderr_trimmed_and_stored(self):
        summary = _make_summary()
        summary.record_attempt(_make_result(stderr="  bad thing  ", attempts=1), duration=0.1)
        assert summary.attempts[0].error == "bad thing"

    def test_empty_stderr_stored_as_none(self):
        summary = _make_summary()
        summary.record_attempt(_make_result(stderr="", attempts=1), duration=0.1)
        assert summary.attempts[0].error is None

    def test_multiple_attempts_recorded(self):
        summary = _make_summary()
        for i in range(1, 4):
            summary.record_attempt(_make_result(exit_code=1, attempts=i), duration=0.05)
        assert summary.total_attempts == 3


# ---------------------------------------------------------------------------
# RunSummary.finalise & derived properties
# ---------------------------------------------------------------------------

class TestRunSummaryFinalise:
    def test_succeeded_flag_set(self):
        summary = _make_summary()
        summary.finalise(succeeded=True)
        assert summary.succeeded is True

    def test_failed_flag_set(self):
        summary = _make_summary()
        summary.finalise(succeeded=False)
        assert summary.succeeded is False

    def test_total_duration_non_negative(self):
        summary = _make_summary()
        summary.finalise(succeeded=True)
        assert summary.total_duration >= 0.0

    def test_total_duration_zero_before_finalise(self):
        summary = _make_summary()
        assert summary.total_duration == 0.0


# ---------------------------------------------------------------------------
# RunSummary.to_dict
# ---------------------------------------------------------------------------

class TestRunSummaryToDict:
    def test_keys_present(self):
        summary = _make_summary()
        summary.record_attempt(_make_result(), duration=0.1)
        summary.finalise(succeeded=True)
        d = summary.to_dict()
        assert {"command", "succeeded", "total_attempts", "total_duration", "attempts"} <= d.keys()

    def test_attempt_keys_present(self):
        summary = _make_summary()
        summary.record_attempt(_make_result(), duration=0.1)
        summary.finalise(succeeded=True)
        attempt = summary.to_dict()["attempts"][0]
        assert {"attempt", "exit_code", "duration", "error"} <= attempt.keys()

    def test_succeeded_reflected(self):
        summary = _make_summary()
        summary.finalise(succeeded=False)
        assert summary.to_dict()["succeeded"] is False

"""Tests for retryctl.condition."""
from __future__ import annotations

import pytest

from retryctl.condition import (
    all_of,
    any_of,
    never,
    on_any_failure,
    on_exit_codes,
    on_output_contains,
)
from retryctl.runner import CommandResult


def _result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    r = CommandResult.__new__(CommandResult)
    r.command = ["echo", "hi"]
    r.exit_code = exit_code
    r.stdout = stdout
    r.stderr = stderr
    r.attempts = 1
    r.elapsed = 0.0
    return r


class TestOnExitCodes:
    def test_matches_listed_code(self):
        pred = on_exit_codes(1, 2)
        assert pred(_result(exit_code=1)) is True

    def test_does_not_match_unlisted_code(self):
        pred = on_exit_codes(1, 2)
        assert pred(_result(exit_code=0)) is False

    def test_single_code(self):
        pred = on_exit_codes(42)
        assert pred(_result(exit_code=42)) is True
        assert pred(_result(exit_code=1)) is False


class TestOnAnyFailure:
    def test_non_zero_triggers_retry(self):
        assert on_any_failure()(_result(exit_code=3)) is True

    def test_zero_does_not_trigger_retry(self):
        assert on_any_failure()(_result(exit_code=0)) is False


class TestOnOutputContains:
    def test_matches_stdout(self):
        pred = on_output_contains("ERROR")
        assert pred(_result(stdout="some ERROR here")) is True

    def test_matches_stderr(self):
        pred = on_output_contains("FATAL")
        assert pred(_result(stderr="FATAL: disk full")) is True

    def test_no_match(self):
        pred = on_output_contains("TIMEOUT")
        assert pred(_result(stdout="all good")) is False


class TestCombinators:
    def test_any_of_true_when_one_matches(self):
        pred = any_of(on_exit_codes(1), on_output_contains("ERR"))
        assert pred(_result(exit_code=0, stdout="ERR")) is True

    def test_any_of_false_when_none_match(self):
        pred = any_of(on_exit_codes(1), on_output_contains("ERR"))
        assert pred(_result(exit_code=0, stdout="ok")) is False

    def test_all_of_true_when_all_match(self):
        pred = all_of(on_exit_codes(1), on_output_contains("ERR"))
        assert pred(_result(exit_code=1, stdout="ERR")) is True

    def test_all_of_false_when_one_misses(self):
        pred = all_of(on_exit_codes(1), on_output_contains("ERR"))
        assert pred(_result(exit_code=1, stdout="ok")) is False

    def test_never_always_false(self):
        assert never()(_result(exit_code=99)) is False

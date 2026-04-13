"""Tests for retryctl.formatter."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from retryctl.formatter import (
    AVAILABLE_FORMATS,
    format_json,
    format_text,
    get_formatter,
)


def _make_result(
    command=("echo", "hi"),
    returncode=0,
    attempts=1,
    succeeded=True,
    elapsed=0.42,
    stdout="hi\n",
    stderr="",
):
    r = MagicMock()
    r.command = command
    r.returncode = returncode
    r.attempts = attempts
    r.succeeded = succeeded
    r.elapsed = elapsed
    r.stdout = stdout
    r.stderr = stderr
    return r


class TestFormatText:
    def test_contains_command(self):
        out = format_text(_make_result())
        assert "echo hi" in out

    def test_contains_exit_code(self):
        out = format_text(_make_result(returncode=1, succeeded=False))
        assert "exit code : 1" in out

    def test_contains_attempts(self):
        out = format_text(_make_result(attempts=3))
        assert "attempts  : 3" in out

    def test_stdout_shown_when_present(self):
        out = format_text(_make_result(stdout="hello"))
        assert "stdout" in out
        assert "hello" in out

    def test_stderr_omitted_when_empty(self):
        out = format_text(_make_result(stderr=""))
        assert "stderr" not in out

    def test_elapsed_formatted(self):
        out = format_text(_make_result(elapsed=1.5))
        assert "1.500s" in out


class TestFormatJson:
    def test_valid_json(self):
        out = format_json(_make_result())
        data = json.loads(out)  # must not raise
        assert isinstance(data, dict)

    def test_fields_present(self):
        data = json.loads(format_json(_make_result(attempts=2, returncode=0)))
        assert data["attempts"] == 2
        assert data["returncode"] == 0
        assert data["succeeded"] is True

    def test_command_is_list(self):
        data = json.loads(format_json(_make_result(command=("ls", "-la"))))
        assert data["command"] == ["ls", "-la"]


class TestGetFormatter:
    def test_returns_text_formatter(self):
        assert get_formatter("text") is format_text

    def test_returns_json_formatter(self):
        assert get_formatter("json") is format_json

    def test_raises_on_unknown_format(self):
        with pytest.raises(ValueError, match="Unknown output format"):
            get_formatter("xml")

    def test_available_formats_contains_text_and_json(self):
        assert "text" in AVAILABLE_FORMATS
        assert "json" in AVAILABLE_FORMATS

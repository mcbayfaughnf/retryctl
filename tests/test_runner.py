"""Tests for retryctl.runner."""

import sys
import pytest
from unittest.mock import patch, MagicMock

from retryctl.runner import run_command, CommandResult
from retryctl.config import RetryConfig


def make_config(**kwargs) -> RetryConfig:
    defaults = dict(
        max_attempts=3,
        backoff_strategy="fixed",
        initial_delay=0.0,
        max_delay=60.0,
        multiplier=2.0,
        increment=1.0,
        timeout=None,
    )
    defaults.update(kwargs)
    return RetryConfig(**defaults)


def make_proc(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestRunCommandSuccess:
    def test_succeeds_on_first_attempt(self):
        config = make_config(max_attempts=3)
        with patch("retryctl.runner.subprocess.run", return_value=make_proc(0, stdout="ok")) as mock_run:
            result = run_command(["echo", "ok"], config)
        assert result.succeeded
        assert result.attempts == 1
        assert result.stdout == "ok"
        mock_run.assert_called_once()

    def test_succeeds_on_third_attempt(self):
        config = make_config(max_attempts=3)
        side_effects = [make_proc(1), make_proc(1), make_proc(0, stdout="done")]
        with patch("retryctl.runner.subprocess.run", side_effect=side_effects):
            with patch("retryctl.runner.time.sleep"):
                result = run_command(["cmd"], config)
        assert result.succeeded
        assert result.attempts == 3


class TestRunCommandFailure:
    def test_returns_last_exit_code_after_all_attempts(self):
        config = make_config(max_attempts=2)
        with patch("retryctl.runner.subprocess.run", return_value=make_proc(42)):
            with patch("retryctl.runner.time.sleep"):
                result = run_command(["false"], config)
        assert not result.succeeded
        assert result.returncode == 42
        assert result.attempts == 2

    def test_timeout_returns_failure(self):
        import subprocess
        config = make_config(max_attempts=2, timeout=0.001)
        with patch("retryctl.runner.subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 0.001)):
            with patch("retryctl.runner.time.sleep"):
                result = run_command(["sleep", "10"], config)
        assert not result.succeeded
        assert result.attempts == 2


class TestRunCommandVerbose:
    def test_verbose_prints_to_stderr(self, capsys):
        config = make_config(max_attempts=1)
        with patch("retryctl.runner.subprocess.run", return_value=make_proc(0)):
            run_command(["echo", "hi"], config, verbose=True)
        captured = capsys.readouterr()
        assert "Attempt 1" in captured.err

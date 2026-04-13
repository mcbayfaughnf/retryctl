"""Tests for retryctl.hooks."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from retryctl.hooks import RetryHooks, default_hooks
from retryctl.runner import CommandResult


def _result(returncode: int = 1, attempts: int = 1) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.returncode = returncode
    r.attempts = attempts
    return r


class TestRetryHooksFireMethods:
    def test_fire_start_calls_callback(self):
        cb = MagicMock()
        hooks = RetryHooks(on_start=cb)
        hooks.fire_start(["echo", "hi"])
        cb.assert_called_once_with(["echo", "hi"])

    def test_fire_start_no_callback_is_noop(self):
        hooks = RetryHooks()
        hooks.fire_start(["echo"])  # should not raise

    def test_fire_retry_calls_callback(self):
        cb = MagicMock()
        hooks = RetryHooks(on_retry=cb)
        result = _result(returncode=2)
        hooks.fire_retry(3, result, 1.5)
        cb.assert_called_once_with(3, result, 1.5)

    def test_fire_retry_no_callback_is_noop(self):
        hooks = RetryHooks()
        hooks.fire_retry(1, _result(), 0.5)  # should not raise

    def test_fire_failure_calls_callback(self):
        cb = MagicMock()
        hooks = RetryHooks(on_failure=cb)
        result = _result(returncode=1)
        hooks.fire_failure(result)
        cb.assert_called_once_with(result)

    def test_fire_success_calls_callback(self):
        cb = MagicMock()
        hooks = RetryHooks(on_success=cb)
        result = _result(returncode=0, attempts=2)
        hooks.fire_success(result)
        cb.assert_called_once_with(result)


class TestDefaultHooks:
    def test_returns_retry_hooks_instance(self):
        hooks = default_hooks()
        assert isinstance(hooks, RetryHooks)

    def test_on_retry_writes_to_stderr(self, capsys):
        hooks = default_hooks(verbose=False)
        hooks.fire_retry(2, _result(returncode=127), 3.0)
        captured = capsys.readouterr()
        assert "attempt 2" in captured.err
        assert "exit 127" in captured.err
        assert "3.00s" in captured.err

    def test_on_failure_writes_to_stderr(self, capsys):
        hooks = default_hooks()
        hooks.fire_failure(_result(returncode=1))
        captured = capsys.readouterr()
        assert "all attempts exhausted" in captured.err
        assert "1" in captured.err

    def test_on_start_silent_when_not_verbose(self, capsys):
        hooks = default_hooks(verbose=False)
        hooks.fire_start(["ls"])
        assert capsys.readouterr().err == ""

    def test_on_start_verbose_writes_to_stderr(self, capsys):
        hooks = default_hooks(verbose=True)
        hooks.fire_start(["ls", "-la"])
        captured = capsys.readouterr()
        assert "ls -la" in captured.err

    def test_on_success_verbose_writes_to_stderr(self, capsys):
        hooks = default_hooks(verbose=True)
        hooks.fire_success(_result(returncode=0, attempts=3))
        captured = capsys.readouterr()
        assert "attempt 3" in captured.err

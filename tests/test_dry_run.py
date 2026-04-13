"""Tests for retryctl.dry_run."""
from __future__ import annotations

import pytest

from retryctl.dry_run import DryRunMiddleware, DryRunRecord
from retryctl.runner import CommandResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _real_next(command, **kwargs) -> CommandResult:
    """Simulates a real downstream callable (should NOT be called in dry-run)."""
    return CommandResult(
        command=command,
        exit_code=42,
        stdout="real",
        stderr="",
        attempts=1,
        elapsed=1.0,
    )


# ---------------------------------------------------------------------------
# DryRunRecord
# ---------------------------------------------------------------------------

class TestDryRunRecord:
    def test_stores_fields(self):
        rec = DryRunRecord(command=["ls"], attempt=1, simulated_exit_code=0)
        assert rec.command == ["ls"]
        assert rec.attempt == 1
        assert rec.simulated_exit_code == 0

    def test_default_exit_code_is_zero(self):
        rec = DryRunRecord(command=["ls"], attempt=1)
        assert rec.simulated_exit_code == 0


# ---------------------------------------------------------------------------
# DryRunMiddleware — construction
# ---------------------------------------------------------------------------

class TestDryRunMiddlewareInit:
    def test_default_exit_code(self):
        mw = DryRunMiddleware()
        assert mw.exit_code == 0

    def test_custom_exit_code(self):
        mw = DryRunMiddleware(exit_code=1)
        assert mw.exit_code == 1

    def test_invalid_exit_code_raises(self):
        with pytest.raises(TypeError):
            DryRunMiddleware(exit_code="zero")  # type: ignore[arg-type]

    def test_enabled_by_default(self):
        assert DryRunMiddleware().enabled is True


# ---------------------------------------------------------------------------
# DryRunMiddleware — dry-run active
# ---------------------------------------------------------------------------

class TestDryRunActive:
    def test_does_not_call_next(self):
        called = []

        def spy_next(command, **kwargs):
            called.append(True)
            return _real_next(command, **kwargs)

        mw = DryRunMiddleware()
        mw(["echo", "hi"], next_call=spy_next)
        assert called == []

    def test_returns_command_result(self):
        mw = DryRunMiddleware(exit_code=0)
        result = mw(["echo", "hi"], next_call=_real_next)
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert result.stdout == "[dry-run]"

    def test_records_invocation(self):
        mw = DryRunMiddleware()
        mw(["ls", "-la"], next_call=_real_next)
        assert mw.call_count == 1
        assert mw.records[0].command == ["ls", "-la"]

    def test_attempt_increments(self):
        mw = DryRunMiddleware()
        mw(["cmd"], next_call=_real_next)
        mw(["cmd"], next_call=_real_next)
        assert mw.records[0].attempt == 1
        assert mw.records[1].attempt == 2

    def test_custom_exit_code_propagated(self):
        mw = DryRunMiddleware(exit_code=2)
        result = mw(["false"], next_call=_real_next)
        assert result.exit_code == 2
        assert mw.records[0].simulated_exit_code == 2


# ---------------------------------------------------------------------------
# DryRunMiddleware — dry-run disabled
# ---------------------------------------------------------------------------

class TestDryRunDisabled:
    def test_delegates_to_next(self):
        mw = DryRunMiddleware(enabled=False)
        result = mw(["echo"], next_call=_real_next)
        assert result.exit_code == 42  # value from _real_next

    def test_no_records_created(self):
        mw = DryRunMiddleware(enabled=False)
        mw(["echo"], next_call=_real_next)
        assert mw.call_count == 0


# ---------------------------------------------------------------------------
# DryRunMiddleware — reset
# ---------------------------------------------------------------------------

class TestDryRunReset:
    def test_clears_records(self):
        mw = DryRunMiddleware()
        mw(["cmd"], next_call=_real_next)
        mw.reset()
        assert mw.call_count == 0

    def test_resets_attempt_counter(self):
        mw = DryRunMiddleware()
        mw(["cmd"], next_call=_real_next)
        mw.reset()
        mw(["cmd"], next_call=_real_next)
        assert mw.records[0].attempt == 1

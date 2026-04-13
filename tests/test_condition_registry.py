"""Tests for retryctl.condition_registry."""
from __future__ import annotations

import pytest

from retryctl.condition_registry import available, lookup, register
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = CommandResult.__new__(CommandResult)
    r.command = ["true"]
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    r.attempts = 1
    r.elapsed = 0.0
    return r


class TestBuiltins:
    def test_any_failure_registered(self):
        pred = lookup("any_failure")
        assert pred(_result(exit_code=1)) is True
        assert pred(_result(exit_code=0)) is False

    def test_never_registered(self):
        assert lookup("never")(_result(exit_code=99)) is False

    def test_on_exit_1_registered(self):
        pred = lookup("on_exit_1")
        assert pred(_result(exit_code=1)) is True
        assert pred(_result(exit_code=2)) is False

    def test_available_returns_sorted_list(self):
        names = available()
        assert names == sorted(names)
        assert "any_failure" in names
        assert "never" in names


class TestRegister:
    def test_custom_predicate_can_be_looked_up(self):
        register("always_retry", lambda r: True)
        assert lookup("always_retry")(_result()) is True

    def test_overwrite_existing(self):
        register("custom_once", lambda r: False)
        register("custom_once", lambda r: True)
        assert lookup("custom_once")(_result()) is True

    def test_non_callable_raises_type_error(self):
        with pytest.raises(TypeError):
            register("bad", "not_a_function")  # type: ignore[arg-type]


class TestLookup:
    def test_unknown_name_raises_key_error(self):
        with pytest.raises(KeyError, match="unknown_xyz"):
            lookup("unknown_xyz")

    def test_error_message_lists_available(self):
        with pytest.raises(KeyError, match="any_failure"):
            lookup("does_not_exist")

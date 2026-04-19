"""Tests for retryctl.suppress."""
import pytest

from retryctl.runner import CommandResult
from retryctl.suppress import SuppressedFailure, SuppressMiddleware, SuppressRule


def _result(exit_code: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(command="echo hi", exit_code=exit_code, stdout=stdout, stderr=stderr, attempts=1)


def _next(result):
    return result


# ---------------------------------------------------------------------------
# SuppressedFailure
# ---------------------------------------------------------------------------

class TestSuppressedFailure:
    def test_stores_result(self):
        r = _result(1)
        exc = SuppressedFailure(r, "test")
        assert exc.result is r

    def test_stores_reason(self):
        exc = SuppressedFailure(_result(1), "my reason")
        assert exc.reason == "my reason"

    def test_message_contains_exit_code(self):
        exc = SuppressedFailure(_result(42), "x")
        assert "42" in str(exc)


# ---------------------------------------------------------------------------
# SuppressRule
# ---------------------------------------------------------------------------

class TestSuppressRule:
    def test_matches_when_predicate_true(self):
        rule = SuppressRule(lambda r: r.exit_code == 1)
        assert rule.matches(_result(1))

    def test_no_match_when_predicate_false(self):
        rule = SuppressRule(lambda r: r.exit_code == 1)
        assert not rule.matches(_result(0))


# ---------------------------------------------------------------------------
# SuppressMiddleware
# ---------------------------------------------------------------------------

class TestSuppressMiddlewareNoRules:
    def test_passes_through_when_no_rules(self):
        mw = SuppressMiddleware()
        r = _result(1)
        assert mw(r, _next) is r


class TestSuppressMiddlewareWithRules:
    def test_raises_on_matching_exit_code(self):
        mw = SuppressMiddleware()
        mw.add_exit_codes([1, 2])
        with pytest.raises(SuppressedFailure) as exc_info:
            mw(_result(1), _next)
        assert exc_info.value.result.exit_code == 1

    def test_no_raise_on_non_matching_exit_code(self):
        mw = SuppressMiddleware()
        mw.add_exit_codes([1, 2])
        result = mw(_result(0), _next)
        assert result.exit_code == 0

    def test_reason_propagated(self):
        mw = SuppressMiddleware()
        mw.add_exit_codes([5], reason="known transient")
        with pytest.raises(SuppressedFailure) as exc_info:
            mw(_result(5), _next)
        assert exc_info.value.reason == "known transient"

    def test_reset_clears_rules(self):
        mw = SuppressMiddleware()
        mw.add_exit_codes([1])
        mw.reset()
        assert mw(_result(1), _next).exit_code == 1

    def test_first_matching_rule_wins(self):
        mw = SuppressMiddleware()
        mw.add_rule(SuppressRule(lambda r: r.exit_code == 3, "rule-a"))
        mw.add_rule(SuppressRule(lambda r: r.exit_code == 3, "rule-b"))
        with pytest.raises(SuppressedFailure) as exc_info:
            mw(_result(3), _next)
        assert exc_info.value.reason == "rule-a"

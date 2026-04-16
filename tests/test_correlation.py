"""Tests for retryctl.correlation."""
import uuid
import pytest
from unittest.mock import MagicMock

from retryctl.correlation import CorrelationContext, CorrelationMiddleware


# ---------------------------------------------------------------------------
# CorrelationContext
# ---------------------------------------------------------------------------

class TestCorrelationContextDefaults:
    def test_run_id_is_valid_uuid(self):
        ctx = CorrelationContext()
        parsed = uuid.UUID(ctx.run_id)
        assert str(parsed) == ctx.run_id

    def test_parent_id_defaults_to_none(self):
        ctx = CorrelationContext()
        assert ctx.parent_id is None

    def test_unique_ids_each_time(self):
        a, b = CorrelationContext(), CorrelationContext()
        assert a.run_id != b.run_id


class TestCorrelationContextChild:
    def test_child_parent_id_matches_parent_run_id(self):
        parent = CorrelationContext()
        child = parent.child()
        assert child.parent_id == parent.run_id

    def test_child_has_new_run_id(self):
        parent = CorrelationContext()
        child = parent.child()
        assert child.run_id != parent.run_id


class TestCorrelationContextAsDict:
    def test_contains_run_id(self):
        ctx = CorrelationContext()
        assert "run_id" in ctx.as_dict()

    def test_no_parent_id_key_when_none(self):
        ctx = CorrelationContext()
        assert "parent_id" not in ctx.as_dict()

    def test_includes_parent_id_when_set(self):
        ctx = CorrelationContext(parent_id="abc")
        d = ctx.as_dict()
        assert d["parent_id"] == "abc"


class TestCorrelationContextStr:
    def test_str_without_parent(self):
        ctx = CorrelationContext(run_id="run1")
        assert str(ctx) == "run1"

    def test_str_with_parent(self):
        ctx = CorrelationContext(run_id="run1", parent_id="parent1")
        assert str(ctx) == "parent1/run1"


# ---------------------------------------------------------------------------
# CorrelationMiddleware
# ---------------------------------------------------------------------------

def _result_with_extra():
    r = MagicMock()
    r.extra = {}
    return r


class TestCorrelationMiddleware:
    def test_attaches_correlation_to_result_extra(self):
        mw = CorrelationMiddleware()
        result = _result_with_extra()
        next_fn = MagicMock(return_value=result)
        mw("echo hi", {}, next_fn)
        assert "correlation" in result.extra

    def test_correlation_contains_run_id(self):
        mw = CorrelationMiddleware()
        result = _result_with_extra()
        next_fn = MagicMock(return_value=result)
        mw("echo hi", {}, next_fn)
        assert "run_id" in result.extra["correlation"]

    def test_reset_replaces_context(self):
        mw = CorrelationMiddleware()
        old_id = mw.context.run_id
        mw.reset()
        assert mw.context.run_id != old_id

    def test_reset_with_explicit_context(self):
        mw = CorrelationMiddleware()
        ctx = CorrelationContext(run_id="fixed-id")
        mw.reset(ctx)
        assert mw.context.run_id == "fixed-id"

    def test_result_without_extra_attr_does_not_raise(self):
        mw = CorrelationMiddleware()
        result = MagicMock(spec=[])  # no 'extra' attribute
        next_fn = MagicMock(return_value=result)
        mw("echo", {}, next_fn)  # should not raise

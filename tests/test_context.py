"""Tests for retryctl.context."""
import time
import uuid

import pytest

from retryctl.context import RunContext


def _ctx(**kwargs) -> RunContext:
    return RunContext(command="echo hi", max_attempts=3, **kwargs)


class TestRunContextDefaults:
    def test_run_id_is_valid_uuid(self):
        ctx = RunContext()
        uuid.UUID(ctx.run_id)  # raises if invalid

    def test_unique_ids_each_time(self):
        assert RunContext().run_id != RunContext().run_id

    def test_attempt_defaults_to_zero(self):
        assert RunContext().attempt == 0

    def test_labels_default_empty(self):
        assert RunContext().labels == {}

    def test_extra_default_empty(self):
        assert RunContext().extra == {}


class TestNextAttempt:
    def test_increments_attempt(self):
        ctx = _ctx(attempt=2)
        assert ctx.next_attempt().attempt == 3

    def test_does_not_mutate_original(self):
        ctx = _ctx(attempt=1)
        ctx.next_attempt()
        assert ctx.attempt == 1

    def test_preserves_run_id(self):
        ctx = _ctx()
        assert ctx.next_attempt().run_id == ctx.run_id


class TestWithLabel:
    def test_adds_label(self):
        ctx = _ctx().with_label("env", "prod")
        assert ctx.labels["env"] == "prod"

    def test_does_not_mutate_original(self):
        ctx = _ctx()
        ctx.with_label("env", "prod")
        assert "env" not in ctx.labels

    def test_overwrites_existing_key(self):
        ctx = _ctx().with_label("env", "prod").with_label("env", "staging")
        assert ctx.labels["env"] == "staging"


class TestWithExtra:
    def test_adds_extra(self):
        ctx = _ctx().with_extra("trace_id", "abc")
        assert ctx.extra["trace_id"] == "abc"

    def test_does_not_mutate_original(self):
        ctx = _ctx()
        ctx.with_extra("x", 1)
        assert "x" not in ctx.extra


class TestElapsed:
    def test_elapsed_is_non_negative(self):
        ctx = RunContext()
        assert ctx.elapsed >= 0

    def test_elapsed_increases_over_time(self):
        ctx = RunContext()
        time.sleep(0.05)
        assert ctx.elapsed >= 0.04


class TestAsDict:
    def test_contains_required_keys(self):
        ctx = _ctx()
        d = ctx.as_dict()
        for key in ("run_id", "command", "max_attempts", "attempt", "elapsed", "labels", "extra"):
            assert key in d

    def test_values_match(self):
        ctx = _ctx(attempt=2)
        d = ctx.as_dict()
        assert d["command"] == "echo hi"
        assert d["attempt"] == 2
        assert d["max_attempts"] == 3

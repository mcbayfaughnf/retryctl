"""Tests for retryctl.fallback_registry."""
from __future__ import annotations

import pytest

import retryctl.fallback_registry as reg
from retryctl.fallback import FallbackPolicy


@pytest.fixture(autouse=True)
def _clean():
    reg.reset_all()
    yield
    reg.reset_all()


class TestGetOrCreate:
    def test_creates_new_policy(self):
        p = reg.get_or_create("a", ["echo", "ok"], on_any_failure=True)
        assert isinstance(p, FallbackPolicy)

    def test_returns_same_instance_on_second_call(self):
        p1 = reg.get_or_create("a", ["echo"], on_any_failure=True)
        p2 = reg.get_or_create("a", ["other"], on_any_failure=True)
        assert p1 is p2

    def test_creates_with_exit_codes(self):
        p = reg.get_or_create("b", ["echo"], on_exit_codes=[1, 2])
        assert 1 in p.on_exit_codes


class TestGet:
    def test_returns_none_for_unknown(self):
        assert reg.get("nope") is None

    def test_returns_registered_policy(self):
        p = reg.get_or_create("x", ["echo"], on_any_failure=True)
        assert reg.get("x") is p


class TestRegister:
    def test_explicit_register(self):
        p = FallbackPolicy(command=["echo"], on_any_failure=True)
        reg.register("manual", p)
        assert reg.get("manual") is p


class TestRemove:
    def test_removes_existing(self):
        reg.get_or_create("r", ["echo"], on_any_failure=True)
        reg.remove("r")
        assert reg.get("r") is None

    def test_remove_missing_is_noop(self):
        reg.remove("missing")  # should not raise


class TestAvailable:
    def test_empty_when_no_policies(self):
        assert reg.available() == []

    def test_returns_sorted_names(self):
        reg.get_or_create("z", ["echo"], on_any_failure=True)
        reg.get_or_create("a", ["echo"], on_any_failure=True)
        assert reg.available() == ["a", "z"]

    def test_reset_all_clears(self):
        reg.get_or_create("x", ["echo"], on_any_failure=True)
        reg.reset_all()
        assert reg.available() == []

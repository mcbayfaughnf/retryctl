"""Tests for retryctl.drain and retryctl.drain_registry."""
from __future__ import annotations

import pytest

from retryctl.drain import (
    DrainActive,
    DrainController,
    DrainMiddleware,
    DrainPolicy,
)
from retryctl.runner import CommandResult
import retryctl.drain_registry as registry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(**kw) -> CommandResult:
    defaults = dict(command="echo hi", exit_code=0, stdout="hi", stderr="", attempts=1, elapsed=0.1)
    defaults.update(kw)
    return CommandResult(**defaults)


def _next(result: CommandResult):
    def _fn(*args, **kwargs):
        return result
    return _fn


# ---------------------------------------------------------------------------
# DrainActive
# ---------------------------------------------------------------------------

class TestDrainActive:
    def test_message_contains_scope(self):
        exc = DrainActive(scope="myapp")
        assert "myapp" in str(exc)

    def test_default_scope(self):
        exc = DrainActive()
        assert "retryctl" in str(exc)

    def test_stores_scope(self):
        exc = DrainActive(scope="svc")
        assert exc.scope == "svc"


# ---------------------------------------------------------------------------
# DrainPolicy
# ---------------------------------------------------------------------------

class TestDrainPolicy:
    def test_defaults(self):
        p = DrainPolicy()
        assert p.scope == "retryctl"
        assert p.raise_on_drain is True

    def test_empty_scope_raises(self):
        with pytest.raises(ValueError):
            DrainPolicy(scope="")


# ---------------------------------------------------------------------------
# DrainController
# ---------------------------------------------------------------------------

class TestDrainController:
    def test_not_draining_initially(self):
        c = DrainController()
        assert c.draining is False

    def test_start_sets_flag(self):
        c = DrainController()
        c.start()
        assert c.draining is True

    def test_reset_clears_flag(self):
        c = DrainController()
        c.start()
        c.reset()
        assert c.draining is False

    def test_start_fires_callbacks(self):
        c = DrainController()
        fired = []
        c.on_drain(lambda: fired.append(1))
        c.start()
        assert fired == [1]

    def test_start_idempotent(self):
        c = DrainController()
        fired = []
        c.on_drain(lambda: fired.append(1))
        c.start()
        c.start()
        assert len(fired) == 1

    def test_remove_callback(self):
        c = DrainController()
        fired = []
        cb = lambda: fired.append(1)
        c.on_drain(cb)
        c.remove_callback(cb)
        c.start()
        assert fired == []


# ---------------------------------------------------------------------------
# DrainMiddleware
# ---------------------------------------------------------------------------

class TestDrainMiddlewareNotDraining:
    def test_delegates_to_next(self):
        ctrl = DrainController()
        mw = DrainMiddleware(ctrl)
        result = _result(exit_code=0)
        assert mw(_next(result)) is result


class TestDrainMiddlewareDraining:
    def test_raises_drain_active_by_default(self):
        ctrl = DrainController()
        ctrl.start()
        mw = DrainMiddleware(ctrl)
        with pytest.raises(DrainActive):
            mw(_next(_result()))

    def test_returns_synthetic_result_when_raise_disabled(self):
        ctrl = DrainController()
        ctrl.start()
        policy = DrainPolicy(raise_on_drain=False)
        mw = DrainMiddleware(ctrl, policy=policy)
        res = mw(_next(_result(exit_code=0)))
        assert res.exit_code == 1
        assert "drain active" in res.stderr

    def test_controller_property(self):
        ctrl = DrainController()
        mw = DrainMiddleware(ctrl)
        assert mw.controller is ctrl


# ---------------------------------------------------------------------------
# drain_registry
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean():
    yield
    registry.reset_all()


class TestDrainRegistry:
    def test_get_or_create_returns_controller(self):
        c = registry.get_or_create("svc")
        assert isinstance(c, DrainController)

    def test_same_instance_on_second_call(self):
        c1 = registry.get_or_create("svc")
        c2 = registry.get_or_create("svc")
        assert c1 is c2

    def test_get_returns_none_if_absent(self):
        assert registry.get("missing") is None

    def test_register_stores_controller(self):
        c = DrainController()
        registry.register("x", c)
        assert registry.get("x") is c

    def test_register_wrong_type_raises(self):
        with pytest.raises(TypeError):
            registry.register("x", object())  # type: ignore

    def test_remove_is_noop_if_absent(self):
        registry.remove("nonexistent")  # should not raise

    def test_drain_all_activates_all(self):
        c1 = registry.get_or_create("a")
        c2 = registry.get_or_create("b")
        registry.drain_all()
        assert c1.draining and c2.draining

    def test_reset_all_clears_registry(self):
        registry.get_or_create("a")
        registry.reset_all()
        assert registry.get("a") is None

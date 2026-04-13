"""Tests for retryctl.signals."""
from __future__ import annotations

import pytest

from retryctl.signals import (
    EVENT_FAILURE,
    EVENT_RETRY,
    EVENT_START,
    EVENT_SUCCESS,
    SignalBus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bus() -> SignalBus:
    return SignalBus()


# ---------------------------------------------------------------------------
# Registration / emission
# ---------------------------------------------------------------------------

class TestSignalBusOn:
    def test_registers_handler(self):
        bus = _make_bus()
        bus.on(EVENT_START, lambda **kw: None)
        assert bus.handler_count(EVENT_START) == 1

    def test_multiple_handlers_same_event(self):
        bus = _make_bus()
        bus.on(EVENT_RETRY, lambda **kw: None)
        bus.on(EVENT_RETRY, lambda **kw: None)
        assert bus.handler_count(EVENT_RETRY) == 2

    def test_unknown_event_raises(self):
        bus = _make_bus()
        with pytest.raises(ValueError, match="Unknown event"):
            bus.on("bogus", lambda **kw: None)


class TestSignalBusEmit:
    def test_emit_calls_handler_with_kwargs(self):
        bus = _make_bus()
        received: list = []
        bus.on(EVENT_SUCCESS, lambda **kw: received.append(kw))
        bus.emit(EVENT_SUCCESS, attempt=1, command="echo hi")
        assert received == [{"attempt": 1, "command": "echo hi"}]

    def test_emit_calls_all_handlers(self):
        bus = _make_bus()
        calls: list = []
        bus.on(EVENT_FAILURE, lambda **kw: calls.append("a"))
        bus.on(EVENT_FAILURE, lambda **kw: calls.append("b"))
        bus.emit(EVENT_FAILURE)
        assert calls == ["a", "b"]

    def test_emit_no_handlers_is_noop(self):
        bus = _make_bus()
        # Should not raise
        bus.emit(EVENT_RETRY, attempt=2)


class TestSignalBusOff:
    def test_off_removes_handler(self):
        bus = _make_bus()
        handler = lambda **kw: None  # noqa: E731
        bus.on(EVENT_START, handler)
        bus.off(EVENT_START, handler)
        assert bus.handler_count(EVENT_START) == 0

    def test_off_unknown_handler_is_noop(self):
        bus = _make_bus()
        # Should not raise
        bus.off(EVENT_START, lambda **kw: None)


class TestSignalBusClear:
    def test_clear_specific_event(self):
        bus = _make_bus()
        bus.on(EVENT_START, lambda **kw: None)
        bus.on(EVENT_SUCCESS, lambda **kw: None)
        bus.clear(EVENT_START)
        assert bus.handler_count(EVENT_START) == 0
        assert bus.handler_count(EVENT_SUCCESS) == 1

    def test_clear_all(self):
        bus = _make_bus()
        bus.on(EVENT_START, lambda **kw: None)
        bus.on(EVENT_RETRY, lambda **kw: None)
        bus.clear()
        assert bus.handler_count(EVENT_START) == 0
        assert bus.handler_count(EVENT_RETRY) == 0


class TestModuleLevelBus:
    def test_module_bus_is_signal_bus_instance(self):
        import retryctl.signals as signals
        assert isinstance(signals.bus, SignalBus)

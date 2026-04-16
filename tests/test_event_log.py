"""Tests for EventLog and EventLogMiddleware."""
from __future__ import annotations

import pytest

from retryctl.event_log import EventEntry, EventLog
from retryctl.event_log_middleware import EventLogMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0, attempts: int = 1) -> CommandResult:
    r = CommandResult.__new__(CommandResult)
    r.command = ["echo", "hi"]
    r.exit_code = exit_code
    r.stdout = ""
    r.stderr = ""
    r.attempts = attempts
    r.elapsed = 0.1
    return r


class TestEventEntry:
    def test_to_dict_has_required_keys(self):
        e = EventEntry(event="start", attempt=1, timestamp=1.0, data={"x": 1})
        d = e.to_dict()
        assert d["event"] == "start"
        assert d["attempt"] == 1
        assert d["timestamp"] == 1.0
        assert d["data"] == {"x": 1}


class TestEventLog:
    def test_record_returns_entry(self):
        log = EventLog()
        entry = log.record("start", attempt=0)
        assert isinstance(entry, EventEntry)

    def test_len_increases(self):
        log = EventLog()
        log.record("start", attempt=0)
        log.record("attempt", attempt=1)
        assert len(log) == 2

    def test_filter_by_event(self):
        log = EventLog()
        log.record("attempt", attempt=1)
        log.record("success", attempt=1)
        log.record("attempt", attempt=2)
        assert len(log.filter("attempt")) == 2
        assert len(log.filter("success")) == 1

    def test_unknown_event_raises(self):
        log = EventLog()
        with pytest.raises(ValueError, match="Unknown event"):
            log.record("bogus", attempt=1)

    def test_clear_empties_log(self):
        log = EventLog()
        log.record("start", attempt=0)
        log.clear()
        assert len(log) == 0

    def test_entries_returns_copy(self):
        log = EventLog()
        log.record("start", attempt=0)
        entries = log.entries()
        entries.clear()
        assert len(log) == 1


class TestEventLogMiddleware:
    def test_records_attempt_and_success(self):
        mw = EventLogMiddleware()
        r = _result(exit_code=0, attempts=1)
        mw(r, lambda x: x)
        events = [e.event for e in mw.log.entries()]
        assert "attempt" in events
        assert "success" in events

    def test_records_failure_on_nonzero(self):
        mw = EventLogMiddleware()
        r = _result(exit_code=1, attempts=2)
        mw(r, lambda x: x)
        events = [e.event for e in mw.log.entries()]
        assert "failure" in events
        assert "success" not in events

    def test_reset_clears_log(self):
        mw = EventLogMiddleware()
        r = _result(exit_code=0)
        mw(r, lambda x: x)
        mw.reset()
        assert len(mw.log) == 0

    def test_accepts_external_log(self):
        log = EventLog()
        mw = EventLogMiddleware(log=log)
        assert mw.log is log

"""Tests for retryctl.priority and retryctl.priority_middleware."""
import pytest
from unittest.mock import MagicMock

from retryctl.priority import PriorityEntry, PriorityQueue, PriorityError
from retryctl.priority_middleware import PriorityMiddleware
from retryctl.runner import CommandResult


def _result(exit_code: int = 0) -> CommandResult:
    r = MagicMock(spec=CommandResult)
    r.exit_code = exit_code
    r.extra = {}
    return r


# ---------------------------------------------------------------------------
# PriorityQueue
# ---------------------------------------------------------------------------

class TestPriorityQueuePush:
    def test_returns_entry(self):
        q = PriorityQueue()
        e = q.push("job", priority=1)
        assert isinstance(e, PriorityEntry)

    def test_negative_priority_raises(self):
        q = PriorityQueue()
        with pytest.raises(PriorityError):
            q.push("job", priority=-1)

    def test_size_increments(self):
        q = PriorityQueue()
        q.push("a")
        q.push("b")
        assert q.size == 2

    def test_empty_initially(self):
        assert PriorityQueue().empty()


class TestPriorityQueuePop:
    def test_pop_returns_lowest_priority_first(self):
        q = PriorityQueue()
        q.push("low", priority=5)
        q.push("high", priority=1)
        assert q.pop().payload == "high"

    def test_pop_empty_raises(self):
        with pytest.raises(IndexError):
            PriorityQueue().pop()

    def test_fifo_for_equal_priority(self):
        q = PriorityQueue()
        q.push("first", priority=0)
        q.push("second", priority=0)
        assert q.pop().payload == "first"


class TestPriorityQueueDrain:
    def test_drain_returns_sorted(self):
        q = PriorityQueue()
        q.push("c", priority=3)
        q.push("a", priority=1)
        q.push("b", priority=2)
        drained = q.drain()
        assert [e.payload for e in drained] == ["a", "b", "c"]

    def test_drain_empties_queue(self):
        q = PriorityQueue()
        q.push("x")
        q.drain()
        assert q.empty()


# ---------------------------------------------------------------------------
# PriorityMiddleware
# ---------------------------------------------------------------------------

class TestPriorityMiddleware:
    def test_delegates_to_next(self):
        mw = PriorityMiddleware()
        res = _result(0)
        result = mw(lambda: res)
        assert result is res

    def test_stores_entry_on_result(self):
        mw = PriorityMiddleware(fixed_priority=2)
        res = _result()
        mw(lambda: res)
        assert "priority_entry" in res.extra
        assert res.extra["priority_entry"].priority == 2

    def test_resolver_called_with_attempt_number(self):
        calls = []
        def resolver(attempt):
            calls.append(attempt)
            return attempt
        mw = PriorityMiddleware(resolver=resolver)
        mw(lambda: _result())
        mw(lambda: _result())
        assert calls == [0, 1]

    def test_reset_clears_queue_and_counter(self):
        mw = PriorityMiddleware()
        mw(lambda: _result())
        mw.reset()
        assert mw.queue.empty()

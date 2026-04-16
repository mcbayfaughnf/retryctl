"""Tests for retryctl.quota."""
import time
import pytest
from retryctl.quota import QuotaCounter, QuotaExceeded, QuotaRegistry


def _counter(limit: int = 3, window: float = 60.0) -> QuotaCounter:
    return QuotaCounter(key="test", limit=limit, window=window)


class TestQuotaCounterInit:
    def test_zero_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            QuotaCounter(key="k", limit=0, window=10.0)

    def test_negative_limit_raises(self):
        with pytest.raises(ValueError, match="limit"):
            QuotaCounter(key="k", limit=-1, window=10.0)

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            QuotaCounter(key="k", limit=1, window=0.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            QuotaCounter(key="k", limit=1, window=-5.0)


class TestQuotaCounterRecord:
    def test_allows_up_to_limit(self):
        c = _counter(limit=3)
        for _ in range(3):
            c.record()
        assert c.current == 3

    def test_raises_on_exceeding_limit(self):
        c = _counter(limit=2)
        c.record()
        c.record()
        with pytest.raises(QuotaExceeded) as exc_info:
            c.record()
        assert exc_info.value.key == "test"
        assert exc_info.value.limit == 2

    def test_reset_clears_counts(self):
        c = _counter(limit=1)
        c.record()
        c.reset()
        assert c.current == 0
        c.record()  # should not raise

    def test_evicts_old_timestamps(self):
        c = _counter(limit=2, window=0.05)
        c.record()
        c.record()
        time.sleep(0.06)
        c.record()  # old ones evicted, should not raise
        assert c.current == 1


class TestQuotaRegistry:
    def test_get_or_create_returns_same_instance(self):
        r = QuotaRegistry()
        a = r.get_or_create("k", 5, 60.0)
        b = r.get_or_create("k", 5, 60.0)
        assert a is b

    def test_reset_all(self):
        r = QuotaRegistry()
        c = r.get_or_create("k", 5, 60.0)
        c.record()
        r.reset()
        assert c.current == 0

    def test_reset_specific_key(self):
        r = QuotaRegistry()
        c1 = r.get_or_create("a", 5, 60.0)
        c2 = r.get_or_create("b", 5, 60.0)
        c1.record()
        c2.record()
        r.reset("a")
        assert c1.current == 0
        assert c2.current == 1

    def test_remove_key(self):
        r = QuotaRegistry()
        r.get_or_create("k", 5, 60.0)
        r.remove("k")
        c2 = r.get_or_create("k", 5, 60.0)
        assert c2.current == 0

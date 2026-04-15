"""Tests for retryctl.metrics."""
import pytest

from retryctl.metrics import MetricsCollector, MetricsSnapshot


def _collector() -> MetricsCollector:
    return MetricsCollector()


# ---------------------------------------------------------------------------
# MetricsSnapshot
# ---------------------------------------------------------------------------

class TestMetricsSnapshot:
    def test_get_returns_value(self):
        snap = MetricsSnapshot(counters={"attempts": 5})
        assert snap.get("attempts") == 5

    def test_get_missing_returns_default(self):
        snap = MetricsSnapshot()
        assert snap.get("missing") == 0

    def test_get_custom_default(self):
        snap = MetricsSnapshot()
        assert snap.get("missing", 99) == 99


# ---------------------------------------------------------------------------
# MetricsCollector – increment
# ---------------------------------------------------------------------------

class TestMetricsCollectorIncrement:
    def test_known_counter_starts_at_zero(self):
        c = _collector()
        assert c.get("attempts") == 0

    def test_increment_by_one(self):
        c = _collector()
        c.increment("attempts")
        assert c.get("attempts") == 1

    def test_increment_by_amount(self):
        c = _collector()
        c.increment("successes", 3)
        assert c.get("successes") == 3

    def test_unknown_name_is_accepted(self):
        c = _collector()
        c.increment("custom_metric")
        assert c.get("custom_metric") == 1

    def test_negative_amount_raises(self):
        c = _collector()
        with pytest.raises(ValueError, match="non-negative"):
            c.increment("attempts", -1)


# ---------------------------------------------------------------------------
# MetricsCollector – reset
# ---------------------------------------------------------------------------

class TestMetricsCollectorReset:
    def test_reset_single_counter(self):
        c = _collector()
        c.increment("attempts", 5)
        c.reset("attempts")
        assert c.get("attempts") == 0

    def test_reset_all_counters(self):
        c = _collector()
        c.increment("attempts", 3)
        c.increment("failures", 2)
        c.reset()
        assert c.get("attempts") == 0
        assert c.get("failures") == 0

    def test_reset_unknown_name_is_noop(self):
        c = _collector()
        c.reset("does_not_exist")  # should not raise


# ---------------------------------------------------------------------------
# MetricsCollector – snapshot
# ---------------------------------------------------------------------------

class TestMetricsCollectorSnapshot:
    def test_snapshot_is_copy(self):
        c = _collector()
        c.increment("attempts", 2)
        snap = c.snapshot()
        c.increment("attempts", 1)
        assert snap.get("attempts") == 2  # snapshot not affected

    def test_snapshot_contains_all_known_counters(self):
        c = _collector()
        snap = c.snapshot()
        for name in MetricsCollector._KNOWN:
            assert name in snap.counters

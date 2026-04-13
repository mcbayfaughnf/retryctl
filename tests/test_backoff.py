"""Unit tests for retryctl backoff strategies."""

import pytest

from retryctl.backoff import (
    BackoffStrategy,
    get_backoff_iterator,
    exponential_backoff,
    fixed_backoff,
    jitter_backoff,
    linear_backoff,
)


def take(n, iterator):
    return [next(iterator) for _ in range(n)]


class TestFixedBackoff:
    def test_constant_values(self):
        it = fixed_backoff(delay=2.0)
        assert take(4, it) == [2.0, 2.0, 2.0, 2.0]


class TestLinearBackoff:
    def test_increases_by_increment(self):
        it = linear_backoff(delay=1.0, increment=2.0)
        assert take(4, it) == [1.0, 3.0, 5.0, 7.0]

    def test_default_increment(self):
        it = linear_backoff(delay=0.0)
        assert take(3, it) == [0.0, 1.0, 2.0]


class TestExponentialBackoff:
    def test_doubles_each_step(self):
        it = exponential_backoff(delay=1.0, multiplier=2.0, max_delay=100.0)
        assert take(4, it) == [1.0, 2.0, 4.0, 8.0]

    def test_respects_max_delay(self):
        it = exponential_backoff(delay=10.0, multiplier=3.0, max_delay=30.0)
        values = take(4, it)
        assert all(v <= 30.0 for v in values)
        assert values[0] == 10.0
        assert values[1] == 30.0


class TestJitterBackoff:
    def test_values_within_bounds(self):
        it = jitter_backoff(delay=1.0, multiplier=2.0, max_delay=16.0)
        values = take(10, it)
        assert all(0 <= v <= 16.0 for v in values)

    def test_non_deterministic(self):
        it = jitter_backoff(delay=1.0, multiplier=2.0, max_delay=100.0)
        values = take(20, it)
        # Very unlikely all values are identical
        assert len(set(values)) > 1


class TestGetBackoffIterator:
    def test_returns_correct_strategy(self):
        it = get_backoff_iterator(BackoffStrategy.FIXED, delay=5.0)
        assert next(it) == 5.0

    def test_invalid_strategy_raises(self):
        with pytest.raises((ValueError, KeyError)):
            get_backoff_iterator("unknown", delay=1.0)  # type: ignore

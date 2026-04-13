"""Backoff strategy implementations for retryctl."""

import random
import time
from enum import Enum
from typing import Iterator


class BackoffStrategy(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"


def fixed_backoff(delay: float, **_) -> Iterator[float]:
    """Yield a constant delay between every retry."""
    while True:
        yield delay


def linear_backoff(delay: float, increment: float = 1.0, **_) -> Iterator[float]:
    """Yield linearly increasing delays."""
    current = delay
    while True:
        yield current
        current += increment


def exponential_backoff(
    delay: float, multiplier: float = 2.0, max_delay: float = 60.0, **_
) -> Iterator[float]:
    """Yield exponentially increasing delays, capped at max_delay."""
    current = delay
    while True:
        yield min(current, max_delay)
        current *= multiplier


def jitter_backoff(
    delay: float, multiplier: float = 2.0, max_delay: float = 60.0, **_
) -> Iterator[float]:
    """Yield exponentially increasing delays with full jitter."""
    current = delay
    while True:
        yield random.uniform(0, min(current, max_delay))
        current *= multiplier


_STRATEGY_MAP = {
    BackoffStrategy.FIXED: fixed_backoff,
    BackoffStrategy.LINEAR: linear_backoff,
    BackoffStrategy.EXPONENTIAL: exponential_backoff,
    BackoffStrategy.JITTER: jitter_backoff,
}


def get_backoff_iterator(strategy: BackoffStrategy, **kwargs) -> Iterator[float]:
    """Return the appropriate backoff iterator for the given strategy."""
    factory = _STRATEGY_MAP.get(strategy)
    if factory is None:
        raise ValueError(f"Unknown backoff strategy: {strategy}")
    return factory(**kwargs)


def wait(seconds: float) -> None:
    """Sleep for the given number of seconds (thin wrapper for testing)."""
    time.sleep(seconds)

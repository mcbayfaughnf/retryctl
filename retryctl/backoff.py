"""Backoff strategies for retry logic."""

import random
from collections.abc import Generator
from enum import Enum
from typing import Any


class BackoffStrategy(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    JITTER = "jitter"


def fixed_backoff(delay: float = 1.0, **_: Any) -> Generator[float, None, None]:
    """Yield a constant delay every time."""
    while True:
        yield delay


def linear_backoff(
    initial: float = 1.0, increment: float = 1.0, maximum: float = 60.0, **_: Any
) -> Generator[float, None, None]:
    """Yield linearly increasing delays."""
    current = initial
    while True:
        yield min(current, maximum)
        current += increment


def exponential_backoff(
    initial: float = 1.0, multiplier: float = 2.0, maximum: float = 60.0, **_: Any
) -> Generator[float, None, None]:
    """Yield exponentially increasing delays."""
    current = initial
    while True:
        yield min(current, maximum)
        current *= multiplier


def jitter_backoff(
    initial: float = 1.0,
    multiplier: float = 2.0,
    maximum: float = 60.0,
    jitter_range: float = 0.5,
    **_: Any,
) -> Generator[float, None, None]:
    """Yield exponentially increasing delays with random jitter."""
    current = initial
    while True:
        jitter = random.uniform(-jitter_range, jitter_range) * current
        yield min(max(0.0, current + jitter), maximum)
        current *= multiplier


_STRATEGY_MAP = {
    BackoffStrategy.FIXED: fixed_backoff,
    BackoffStrategy.LINEAR: linear_backoff,
    BackoffStrategy.EXPONENTIAL: exponential_backoff,
    BackoffStrategy.JITTER: jitter_backoff,
}


def get_backoff_sequence(config: Any) -> Generator[float, None, None]:
    """Return a backoff generator based on the config's strategy."""
    strategy_fn = _STRATEGY_MAP[BackoffStrategy(config.backoff_strategy)]
    return strategy_fn(**config.backoff_kwargs)

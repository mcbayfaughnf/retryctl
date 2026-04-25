"""Sampling middleware — probabilistically forward attempts to next handler.

Useful for canary-style retry runs where only a fraction of retried
attempts should actually execute (e.g. for shadow testing or cost control).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from retryctl.runner import CommandResult


class SampleSkipped(Exception):
    """Raised when an attempt is skipped due to sampling."""

    def __init__(self, rate: float, attempt: int) -> None:
        self.rate = rate
        self.attempt = attempt
        super().__init__(
            f"attempt {attempt} skipped by sampler (rate={rate:.2f})"
        )


@dataclass
class SamplingPolicy:
    """Configuration for the sampling middleware."""

    rate: float = 1.0  # fraction of attempts to forward [0.0, 1.0]
    skip_first: bool = False  # when True, always forward attempt 1

    def __post_init__(self) -> None:
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError(
                f"rate must be between 0.0 and 1.0, got {self.rate}"
            )

    def should_sample(self, attempt: int, rng: Optional[random.Random] = None) -> bool:
        """Return True if this attempt should be forwarded."""
        if self.skip_first and attempt == 1:
            return True
        r = (rng or random).random()
        return r < self.rate


@dataclass
class SamplingMiddleware:
    """Middleware that probabilistically forwards attempts."""

    policy: SamplingPolicy
    _attempt: int = field(default=0, init=False, repr=False)
    _skipped: int = field(default=0, init=False, repr=False)
    _rng: Optional[random.Random] = field(default=None, init=False, repr=False)

    def seed(self, seed_value: int) -> None:
        """Seed the internal RNG for deterministic behaviour in tests."""
        self._rng = random.Random(seed_value)

    def __call__(
        self, next_handler: Callable[..., CommandResult], *args, **kwargs
    ) -> CommandResult:
        self._attempt += 1
        if not self.policy.should_sample(self._attempt, self._rng):
            self._skipped += 1
            raise SampleSkipped(rate=self.policy.rate, attempt=self._attempt)
        return next_handler(*args, **kwargs)

    @property
    def attempt_count(self) -> int:
        return self._attempt

    @property
    def skipped_count(self) -> int:
        return self._skipped

    def reset(self) -> None:
        self._attempt = 0
        self._skipped = 0
        self._rng = None

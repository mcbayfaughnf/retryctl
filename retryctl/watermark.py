"""High/low watermark tracking for retry attempt counts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class WatermarkError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class WatermarkPolicy:
    high: int
    low: int

    def __post_init__(self) -> None:
        if self.high <= 0:
            raise WatermarkError("high watermark must be positive")
        if self.low < 0:
            raise WatermarkError("low watermark must be non-negative")
        if self.low >= self.high:
            raise WatermarkError("low watermark must be less than high watermark")


@dataclass
class WatermarkTracker:
    policy: WatermarkPolicy
    _count: int = field(default=0, init=False)
    _peak: int = field(default=0, init=False)
    _above_high: bool = field(default=False, init=False)

    def record(self, exit_code: int) -> None:
        """Record an attempt outcome; increments count on failure."""
        if exit_code != 0:
            self._count += 1
            if self._count > self._peak:
                self._peak = self._count
            if self._count >= self.policy.high:
                self._above_high = True
        else:
            if self._count > self.policy.low:
                self._count = max(self._count - 1, self.policy.low)
            if self._count <= self.policy.low:
                self._above_high = False

    @property
    def count(self) -> int:
        return self._count

    @property
    def peak(self) -> int:
        return self._peak

    @property
    def above_high(self) -> bool:
        return self._above_high

    @property
    def below_low(self) -> bool:
        return self._count <= self.policy.low

    def reset(self) -> None:
        self._count = 0
        self._peak = 0
        self._above_high = False

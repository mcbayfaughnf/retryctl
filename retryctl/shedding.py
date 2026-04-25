"""Load shedding middleware — drops requests when system load exceeds a threshold."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


class LoadShedded(Exception):
    """Raised when a request is dropped due to high load."""

    def __init__(self, load: float, threshold: float) -> None:
        self.load = load
        self.threshold = threshold
        super().__init__(
            f"Request shed: system load {load:.2f} exceeds threshold {threshold:.2f}"
        )


@dataclass
class SheddingPolicy:
    threshold: float
    window: float = 5.0
    load_fn: Optional[Callable[[], float]] = None

    def __post_init__(self) -> None:
        if self.threshold <= 0.0:
            raise ValueError("threshold must be positive")
        if self.threshold > 1.0:
            raise ValueError("threshold must be <= 1.0")
        if self.window <= 0.0:
            raise ValueError("window must be positive")


@dataclass
class SheddingTracker:
    policy: SheddingPolicy
    _samples: list = field(default_factory=list, init=False)

    def record(self, success: bool) -> None:
        now = time.monotonic()
        self._samples.append((now, success))
        cutoff = now - self.policy.window
        self._samples = [(t, s) for t, s in self._samples if t >= cutoff]

    def current_load(self) -> float:
        if self.policy.load_fn is not None:
            return self.policy.load_fn()
        if not self._samples:
            return 0.0
        failures = sum(1 for _, s in self._samples if not s)
        return failures / len(self._samples)

    def should_shed(self) -> bool:
        return self.current_load() >= self.policy.threshold

    def reset(self) -> None:
        self._samples.clear()

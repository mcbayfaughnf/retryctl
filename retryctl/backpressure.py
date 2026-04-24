"""Backpressure: slow down retry attempts when the system signals overload.

A BackpressurePolicy holds a threshold (0.0–1.0) representing the fraction
of capacity that triggers backpressure.  A BackpressureTracker accumulates
load samples and exposes whether backpressure is currently active.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence


class BackpressureActive(Exception):
    """Raised when backpressure is active and the caller should back off."""

    def __init__(self, load: float, threshold: float) -> None:
        self.load = load
        self.threshold = threshold
        super().__init__(
            f"backpressure active: load {load:.2f} >= threshold {threshold:.2f}"
        )


@dataclass
class BackpressurePolicy:
    """Configuration for backpressure detection."""

    threshold: float = 0.8
    window: int = 5  # number of recent samples to consider

    def __post_init__(self) -> None:
        if not (0.0 < self.threshold <= 1.0):
            raise ValueError("threshold must be in (0.0, 1.0]")
        if self.window < 1:
            raise ValueError("window must be >= 1")


@dataclass
class BackpressureTracker:
    """Tracks load samples and determines whether backpressure is active."""

    policy: BackpressurePolicy = field(default_factory=BackpressurePolicy)
    _samples: list[float] = field(default_factory=list, init=False, repr=False)

    def record(self, load: float) -> None:
        """Record a load sample in [0.0, 1.0]."""
        if not (0.0 <= load <= 1.0):
            raise ValueError("load sample must be in [0.0, 1.0]")
        self._samples.append(load)
        if len(self._samples) > self.policy.window:
            self._samples = self._samples[-self.policy.window :]

    @property
    def current_load(self) -> float:
        """Average load across the current window (0.0 if no samples)."""
        if not self._samples:
            return 0.0
        return sum(self._samples) / len(self._samples)

    @property
    def is_active(self) -> bool:
        """Return True when average load meets or exceeds the threshold."""
        return self.current_load >= self.policy.threshold

    def check(self) -> None:
        """Raise BackpressureActive if backpressure is currently active."""
        load = self.current_load
        if load >= self.policy.threshold:
            raise BackpressureActive(load, self.policy.threshold)

    def reset(self) -> None:
        """Clear all recorded samples."""
        self._samples.clear()

"""Hedged request middleware: launches a speculative second attempt after a
defined delay if the first has not yet completed, returning whichever result
arrives first.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from retryctl.runner import CommandResult


class HedgeError(Exception):
    """Raised when the hedge configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class HedgePolicy:
    """Configuration for hedged execution."""

    delay: float          # seconds before launching the speculative attempt
    max_hedges: int = 1   # how many speculative attempts to allow

    def __post_init__(self) -> None:
        if self.delay <= 0:
            raise HedgeError(f"delay must be positive, got {self.delay}")
        if self.max_hedges < 1:
            raise HedgeError(f"max_hedges must be >= 1, got {self.max_hedges}")


@dataclass
class HedgeMiddleware:
    """Middleware that implements hedged requests.

    After *policy.delay* seconds, a duplicate call to *next_fn* is fired in a
    background thread.  Whichever invocation finishes first with exit_code == 0
    is returned; if both fail the result from the original call is used.
    """

    policy: HedgePolicy
    _hedge_count: int = field(default=0, init=False, repr=False)

    def __call__(
        self,
        next_fn: Callable[[], CommandResult],
        *,
        _sleep: Callable[[float], None] | None = None,
    ) -> CommandResult:
        import time

        sleep = _sleep if _sleep is not None else time.sleep

        result_holder: list[CommandResult] = []
        event = threading.Event()
        lock = threading.Lock()

        def run_and_store() -> None:
            res = next_fn()
            with lock:
                if not event.is_set():
                    result_holder.append(res)
                    if res.exit_code == 0:
                        event.set()

        primary = threading.Thread(target=run_and_store, daemon=True)
        primary.start()

        hedges_fired = 0
        while not event.is_set() and hedges_fired < self.policy.max_hedges:
            sleep(self.policy.delay)
            if event.is_set():
                break
            hedges_fired += 1
            self._hedge_count += 1
            hedge = threading.Thread(target=run_and_store, daemon=True)
            hedge.start()

        primary.join()
        with lock:
            successes = [r for r in result_holder if r.exit_code == 0]
            return successes[0] if successes else result_holder[0]

    @property
    def hedge_count(self) -> int:
        """Total speculative attempts fired so far."""
        return self._hedge_count

    def reset(self) -> None:
        """Reset the hedge counter."""
        self._hedge_count = 0

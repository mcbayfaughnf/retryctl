"""Rate-limiting / throttle helpers for retryctl.

Provides a simple token-bucket throttle that can be used to cap how
frequently retry attempts are allowed to start, independent of the
backoff delay between them.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


class ThrottleExceeded(Exception):
    """Raised when the throttle bucket is exhausted and *block=False*."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Throttle exceeded; retry after {retry_after:.2f}s"
        )


@dataclass
class TokenBucket:
    """Token-bucket rate limiter.

    Parameters
    ----------
    rate:
        Tokens replenished per second.
    capacity:
        Maximum tokens the bucket can hold.
    """

    rate: float
    capacity: float
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        if self.rate <= 0:
            raise ValueError("rate must be positive")
        if self.capacity <= 0:
            raise ValueError("capacity must be positive")
        self._tokens = self.capacity
        self._last_refill = time.monotonic()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._last_refill = now

    def available(self) -> float:
        """Return the current token count (after refill)."""
        self._refill()
        return self._tokens

    def retry_after(self) -> float:
        """Seconds until at least one token is available."""
        self._refill()
        if self._tokens >= 1.0:
            return 0.0
        return (1.0 - self._tokens) / self.rate

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def consume(self, tokens: float = 1.0, *, block: bool = True) -> None:
        """Consume *tokens* from the bucket.

        Parameters
        ----------
        tokens:
            Number of tokens to consume (default 1).
        block:
            If *True* (default) sleep until enough tokens are available.
            If *False* raise :exc:`ThrottleExceeded` instead.
        """
        self._refill()
        if self._tokens < tokens:
            wait = (tokens - self._tokens) / self.rate
            if not block:
                raise ThrottleExceeded(retry_after=wait)
            time.sleep(wait)
            self._refill()
        self._tokens -= tokens

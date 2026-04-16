"""Middleware that enforces per-key attempt quotas."""
from __future__ import annotations
from typing import Callable, Optional
from retryctl.quota import QuotaRegistry, QuotaExceeded
from retryctl.runner import CommandResult


class QuotaMiddleware:
    """Reject attempts once a key's quota is exhausted within the window."""

    def __init__(
        self,
        key: str,
        limit: int,
        window: float,
        registry: Optional[QuotaRegistry] = None,
    ) -> None:
        self._key = key
        self._limit = limit
        self._window = window
        self._registry = registry or QuotaRegistry()

    def __call__(self, next_fn: Callable[..., CommandResult], *args, **kwargs) -> CommandResult:
        counter = self._registry.get_or_create(self._key, self._limit, self._window)
        counter.record()  # raises QuotaExceeded if limit hit
        return next_fn(*args, **kwargs)

    def current(self) -> int:
        counter = self._registry.get_or_create(self._key, self._limit, self._window)
        return counter.current

    def reset(self) -> None:
        self._registry.reset(self._key)

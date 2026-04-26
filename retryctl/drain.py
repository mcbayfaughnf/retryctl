"""Drain middleware — prevents new attempts once a drain signal is set.

Useful for graceful shutdown: once draining begins, in-flight attempts
complete but no new ones are started.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from retryctl.runner import CommandResult


class DrainActive(Exception):
    """Raised when an attempt is blocked because the drain flag is set."""

    def __init__(self, scope: str = "retryctl") -> None:
        self.scope = scope
        super().__init__(f"[{scope}] drain is active — no new attempts accepted")


@dataclass
class DrainPolicy:
    """Configuration for drain behaviour."""

    scope: str = "retryctl"
    raise_on_drain: bool = True

    def __post_init__(self) -> None:
        if not self.scope:
            raise ValueError("scope must be a non-empty string")


class DrainController:
    """Thread-safe flag that tracks whether the system is draining."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._draining = False
        self._callbacks: list[Callable[[], None]] = []

    @property
    def draining(self) -> bool:
        with self._lock:
            return self._draining

    def start(self) -> None:
        """Activate the drain flag and fire registered callbacks."""
        with self._lock:
            if self._draining:
                return
            self._draining = True
        for cb in list(self._callbacks):
            cb()

    def reset(self) -> None:
        with self._lock:
            self._draining = False

    def on_drain(self, callback: Callable[[], None]) -> None:
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        self._callbacks = [c for c in self._callbacks if c is not callback]


class DrainMiddleware:
    """Middleware that blocks new attempts when the drain controller is active."""

    def __init__(
        self,
        controller: DrainController,
        policy: Optional[DrainPolicy] = None,
    ) -> None:
        self._controller = controller
        self._policy = policy or DrainPolicy()

    def __call__(
        self,
        next_fn: Callable[..., CommandResult],
        *args,
        **kwargs,
    ) -> CommandResult:
        if self._controller.draining:
            if self._policy.raise_on_drain:
                raise DrainActive(self._policy.scope)
            # Return a synthetic failure result without executing
            return CommandResult(
                command=kwargs.get("command", args[0] if args else ""),
                exit_code=1,
                stdout="",
                stderr=f"drain active: {self._policy.scope}",
                attempts=0,
                elapsed=0.0,
            )
        return next_fn(*args, **kwargs)

    @property
    def controller(self) -> DrainController:
        return self._controller

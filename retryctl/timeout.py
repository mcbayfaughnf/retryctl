"""Timeout utilities for retryctl.

Provides per-attempt and overall run timeout enforcement.
"""
from __future__ import annotations

import signal
import contextlib
from typing import Generator


class TimeoutExpired(Exception):
    """Raised when an attempt or overall run exceeds its allowed duration."""

    def __init__(self, seconds: float, scope: str = "attempt") -> None:
        self.seconds = seconds
        self.scope = scope
        super().__init__(f"{scope} timeout of {seconds}s expired")


@contextlib.contextmanager
def timeout_context(seconds: float | None, scope: str = "attempt") -> Generator[None, None, None]:
    """Context manager that raises *TimeoutExpired* after *seconds*.

    If *seconds* is ``None`` or ``0`` the context manager is a no-op so
    callers can always wrap their code without checking first.

    Only works on POSIX systems (requires SIGALRM).
    """
    if not seconds:
        yield
        return

    if not hasattr(signal, "SIGALRM"):  # pragma: no cover – Windows
        yield
        return

    def _handler(signum: int, frame: object) -> None:  # noqa: ARG001
        raise TimeoutExpired(seconds, scope)

    old_handler = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)


def remaining(overall_deadline: float | None, elapsed: float) -> float | None:
    """Return seconds left before *overall_deadline* is breached.

    Returns ``None`` when there is no overall deadline, and ``0.0`` when the
    deadline has already passed (callers should treat this as expired).
    """
    if overall_deadline is None:
        return None
    left = overall_deadline - elapsed
    return max(left, 0.0)

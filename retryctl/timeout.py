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

    .. warning::
        This context manager is **not** re-entrant.  Nesting two
        ``timeout_context`` calls will cause the inner one to overwrite the
        outer SIGALRM timer.  The outer timer is restored on exit, but any
        time already elapsed against it is lost.
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


def deadline_exceeded(overall_deadline: float | None, elapsed: float) -> bool:
    """Return ``True`` when *elapsed* has met or surpassed *overall_deadline*.

    Convenience wrapper around :func:`remaining` so callers can write a
    simple boolean check instead of comparing the return value themselves::

        if deadline_exceeded(deadline, elapsed):
            raise TimeoutExpired(deadline, scope="overall")

    Returns ``False`` when *overall_deadline* is ``None`` (no deadline set).
    """
    left = remaining(overall_deadline, elapsed)
    return left is not None and left == 0.0

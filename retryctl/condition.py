"""Retry condition predicates — decide whether a failed attempt should be retried."""
from __future__ import annotations

from typing import Callable, Iterable

from retryctl.runner import CommandResult

# A predicate that returns True when the run should be retried.
RetryPredicate = Callable[[CommandResult], bool]


def on_exit_codes(*codes: int) -> RetryPredicate:
    """Retry when the exit code is one of *codes*."""
    code_set = frozenset(codes)

    def _check(result: CommandResult) -> bool:
        return result.exit_code in code_set

    _check.__name__ = f"on_exit_codes({', '.join(str(c) for c in codes)})"
    return _check


def on_any_failure() -> RetryPredicate:
    """Retry on any non-zero exit code."""

    def _check(result: CommandResult) -> bool:
        return result.exit_code != 0

    _check.__name__ = "on_any_failure"
    return _check


def on_output_contains(substring: str) -> RetryPredicate:
    """Retry when *substring* appears in stdout or stderr."""

    def _check(result: CommandResult) -> bool:
        haystack = (result.stdout or "") + (result.stderr or "")
        return substring in haystack

    _check.__name__ = f"on_output_contains({substring!r})"
    return _check


def any_of(*predicates: RetryPredicate) -> RetryPredicate:
    """Retry when *any* of the supplied predicates returns True."""

    def _check(result: CommandResult) -> bool:
        return any(p(result) for p in predicates)

    _check.__name__ = "any_of(" + ", ".join(p.__name__ for p in predicates) + ")"
    return _check


def all_of(*predicates: RetryPredicate) -> RetryPredicate:
    """Retry when *all* of the supplied predicates return True."""

    def _check(result: CommandResult) -> bool:
        return all(p(result) for p in predicates)

    _check.__name__ = "all_of(" + ", ".join(p.__name__ for p in predicates) + ")"
    return _check


def never() -> RetryPredicate:
    """Never retry — always accept the result."""

    def _check(result: CommandResult) -> bool:  # noqa: ARG001
        return False

    _check.__name__ = "never"
    return _check

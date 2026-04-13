"""Lifecycle hooks for retry events in retryctl."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable, Optional

from retryctl.runner import CommandResult


@dataclass
class RetryHooks:
    """Collection of optional callbacks invoked at key points in the retry loop."""

    # Called before the very first attempt.
    on_start: Optional[Callable[[list[str]], None]] = field(default=None)

    # Called after every failed attempt.
    # Signature: (attempt: int, result: CommandResult, delay: float) -> None
    on_retry: Optional[Callable[[int, CommandResult, float], None]] = field(default=None)

    # Called when all attempts are exhausted without success.
    on_failure: Optional[Callable[[CommandResult], None]] = field(default=None)

    # Called when the command succeeds.
    on_success: Optional[Callable[[CommandResult], None]] = field(default=None)

    def fire_start(self, cmd: list[str]) -> None:
        if self.on_start:
            self.on_start(cmd)

    def fire_retry(self, attempt: int, result: CommandResult, delay: float) -> None:
        if self.on_retry:
            self.on_retry(attempt, result, delay)

    def fire_failure(self, result: CommandResult) -> None:
        if self.on_failure:
            self.on_failure(result)

    def fire_success(self, result: CommandResult) -> None:
        if self.on_success:
            self.on_success(result)


def default_hooks(verbose: bool = False) -> RetryHooks:
    """Return a RetryHooks instance with sensible stderr logging callbacks."""

    def _on_start(cmd: list[str]) -> None:
        if verbose:
            print(f"[retryctl] running: {' '.join(cmd)}", file=sys.stderr)

    def _on_retry(attempt: int, result: CommandResult, delay: float) -> None:
        print(
            f"[retryctl] attempt {attempt} failed (exit {result.returncode}); "
            f"retrying in {delay:.2f}s",
            file=sys.stderr,
        )

    def _on_failure(result: CommandResult) -> None:
        print(
            f"[retryctl] all attempts exhausted. last exit code: {result.returncode}",
            file=sys.stderr,
        )

    def _on_success(result: CommandResult) -> None:
        if verbose:
            print(
                f"[retryctl] succeeded on attempt {result.attempts}",
                file=sys.stderr,
            )

    return RetryHooks(
        on_start=_on_start,
        on_retry=_on_retry,
        on_failure=_on_failure,
        on_success=_on_success,
    )

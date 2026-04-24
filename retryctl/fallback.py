"""Fallback middleware: run an alternative command when the primary fails."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from retryctl.runner import CommandResult


class FallbackError(Exception):
    """Raised when fallback configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class FallbackPolicy:
    """Defines when and how to invoke a fallback command."""

    command: Sequence[str]
    on_exit_codes: Sequence[int] = field(default_factory=lambda: [])
    on_any_failure: bool = False

    def __post_init__(self) -> None:
        if not self.command:
            raise FallbackError("fallback command must not be empty")
        if not self.on_any_failure and not self.on_exit_codes:
            raise FallbackError(
                "fallback policy requires on_any_failure=True or at least one exit code"
            )

    def should_fallback(self, result: CommandResult) -> bool:
        """Return True if the result warrants invoking the fallback."""
        if result.exit_code == 0:
            return False
        if self.on_any_failure:
            return True
        return result.exit_code in self.on_exit_codes


@dataclass
class FallbackResult:
    """Wraps the outcome of a fallback invocation."""

    original: CommandResult
    fallback: CommandResult
    triggered: bool = True

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FallbackResult(triggered={self.triggered}, "
            f"original_exit={self.original.exit_code}, "
            f"fallback_exit={self.fallback.exit_code})"
        )


class FallbackMiddleware:
    """Middleware that invokes a fallback command when the primary fails."""

    def __init__(
        self,
        policy: FallbackPolicy,
        runner: Optional[Callable[[Sequence[str]], CommandResult]] = None,
    ) -> None:
        self._policy = policy
        self._runner = runner or _default_runner
        self._last_fallback: Optional[FallbackResult] = None

    def __call__(
        self, command: Sequence[str], next_fn: Callable[[Sequence[str]], CommandResult]
    ) -> CommandResult:
        result = next_fn(command)
        if self._policy.should_fallback(result):
            fb_result = self._runner(self._policy.command)
            self._last_fallback = FallbackResult(original=result, fallback=fb_result)
            return fb_result
        self._last_fallback = FallbackResult(
            original=result, fallback=result, triggered=False
        )
        return result

    @property
    def last_fallback(self) -> Optional[FallbackResult]:
        return self._last_fallback

    def reset(self) -> None:
        self._last_fallback = None


def _default_runner(command: Sequence[str]) -> CommandResult:
    import subprocess

    proc = subprocess.run(command, capture_output=True, text=True)
    return CommandResult(
        command=list(command),
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        attempts=1,
    )

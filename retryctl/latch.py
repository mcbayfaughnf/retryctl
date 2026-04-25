"""One-shot latch middleware: stops retrying once a success condition is latched.

Once a successful result is observed the latch closes and every subsequent
call is short-circuited with the cached winning result, preventing redundant
retries in fan-out / scatter scenarios.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from retryctl.runner import CommandResult


class LatchAlreadyTripped(Exception):
    """Raised when the latch has already been tripped and no further calls should proceed."""

    def __init__(self, result: CommandResult) -> None:
        self.result = result
        super().__init__(
            f"Latch already tripped with exit_code={result.exit_code} "
            f"after {result.attempts} attempt(s)"
        )


@dataclass
class LatchPolicy:
    """Configuration for the latch behaviour."""

    success_codes: tuple[int, ...] = (0,)
    raise_on_tripped: bool = False

    def __post_init__(self) -> None:
        if not self.success_codes:
            raise ValueError("success_codes must contain at least one exit code")

    def is_success(self, result: CommandResult) -> bool:
        return result.exit_code in self.success_codes


@dataclass
class LatchState:
    """Mutable state shared across middleware invocations."""

    _tripped: bool = field(default=False, init=False)
    _winning_result: Optional[CommandResult] = field(default=None, init=False)

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def winning_result(self) -> Optional[CommandResult]:
        return self._winning_result

    def trip(self, result: CommandResult) -> None:
        self._tripped = True
        self._winning_result = result

    def reset(self) -> None:
        self._tripped = False
        self._winning_result = None


class LatchMiddleware:
    """Middleware that short-circuits once a winning result has been latched."""

    def __init__(
        self,
        policy: Optional[LatchPolicy] = None,
        state: Optional[LatchState] = None,
    ) -> None:
        self._policy = policy or LatchPolicy()
        self._state = state or LatchState()

    def __call__(
        self, next_fn: Callable[[str], CommandResult], command: str
    ) -> CommandResult:
        if self._state.tripped:
            if self._policy.raise_on_tripped:
                raise LatchAlreadyTripped(self._state.winning_result)  # type: ignore[arg-type]
            return self._state.winning_result  # type: ignore[return-value]

        result = next_fn(command)

        if self._policy.is_success(result):
            self._state.trip(result)

        return result

    @property
    def state(self) -> LatchState:
        return self._state

    def reset(self) -> None:
        self._state.reset()

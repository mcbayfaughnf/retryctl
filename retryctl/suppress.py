"""Suppress middleware: skip retry on matching exit codes or exceptions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from retryctl.runner import CommandResult


class SuppressedFailure(Exception):
    """Raised when a result matches a suppress rule and should not be retried."""

    def __init__(self, result: CommandResult, reason: str) -> None:
        super().__init__(f"Suppressed ({reason}): exit {result.exit_code}")
        self.result = result
        self.reason = reason


@dataclass
class SuppressRule:
    """A single suppress rule with a predicate and a human-readable reason."""

    predicate: Callable[[CommandResult], bool]
    reason: str = "suppressed"

    def matches(self, result: CommandResult) -> bool:
        return self.predicate(result)


@dataclass
class SuppressMiddleware:
    """Middleware that raises SuppressedFailure when a rule matches.

    Suppressed results are treated as terminal — no further retries occur.
    """

    rules: list[SuppressRule] = field(default_factory=list)

    def add_rule(self, rule: SuppressRule) -> None:
        self.rules.append(rule)

    def add_exit_codes(self, codes: Iterable[int], reason: str = "exit code suppressed") -> None:
        code_set = frozenset(codes)
        self.add_rule(SuppressRule(lambda r, cs=code_set: r.exit_code in cs, reason))

    def __call__(self, result: CommandResult, next_fn: Callable) -> CommandResult:
        result = next_fn(result)
        for rule in self.rules:
            if rule.matches(result):
                raise SuppressedFailure(result, rule.reason)
        return result

    def reset(self) -> None:
        self.rules.clear()

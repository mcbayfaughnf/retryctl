"""Middleware that gates retries through a RetryPredicate.

When a :class:`RetryPredicate` returns *False* for a result the middleware
marks the result as final so the pipeline does not schedule another attempt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from retryctl.condition import RetryPredicate, on_any_failure
from retryctl.runner import CommandResult

# Type alias for the next callable in a middleware chain.
_Next = Callable[[CommandResult], CommandResult]


@dataclass
class ConditionMiddleware:
    """Wraps a :class:`RetryPredicate` as pipeline middleware.

    Parameters
    ----------
    predicate:
        Called with each :class:`CommandResult`.  When it returns *False* the
        ``should_retry`` flag on the result is set to *False*, preventing
        further attempts.
    """

    predicate: RetryPredicate = field(default_factory=on_any_failure)

    def __call__(self, result: CommandResult, next_fn: _Next) -> CommandResult:
        """Evaluate *predicate* and update *result* before passing downstream."""
        if not self.predicate(result):
            # Signal to the runner that no further retry is desired.
            result.should_retry = False
        return next_fn(result)

    # ------------------------------------------------------------------
    # Convenience factories
    # ------------------------------------------------------------------

    @classmethod
    def from_name(cls, name: str) -> "ConditionMiddleware":
        """Build a :class:`ConditionMiddleware` from a registry name.

        Parameters
        ----------
        name:
            A condition name as registered in
            :mod:`retryctl.condition_registry`.

        Raises
        ------
        KeyError
            If *name* is not found in the condition registry.
        """
        from retryctl.condition_registry import lookup  # local to avoid cycles

        return cls(predicate=lookup(name))

    @classmethod
    def from_predicate(cls, predicate: RetryPredicate) -> "ConditionMiddleware":
        """Build a :class:`ConditionMiddleware` directly from a callable.

        This is a thin convenience wrapper around the default constructor that
        makes call-sites more explicit when constructing from a predicate
        rather than a registry name.

        Parameters
        ----------
        predicate:
            Any callable that accepts a :class:`CommandResult` and returns a
            ``bool`` indicating whether a retry should be attempted.
        """
        return cls(predicate=predicate)

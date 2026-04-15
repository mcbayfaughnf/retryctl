"""Middleware that records attempt/success/failure metrics."""
from __future__ import annotations

from typing import Callable

from retryctl.metrics import MetricsCollector
from retryctl.runner import CommandResult


class MetricsMiddleware:
    """Wraps the next handler and updates a :class:`MetricsCollector`.

    Parameters
    ----------
    collector:
        The shared :class:`MetricsCollector` to update.
    success_codes:
        Exit codes considered successful.  Defaults to ``{0}``.
    """

    def __init__(
        self,
        collector: MetricsCollector,
        success_codes: frozenset[int] | None = None,
    ) -> None:
        self._collector = collector
        self._success_codes: frozenset[int] = (
            frozenset({0}) if success_codes is None else frozenset(success_codes)
        )

    # ------------------------------------------------------------------
    # Callable protocol
    # ------------------------------------------------------------------

    def __call__(
        self,
        next_handler: Callable[..., CommandResult],
        /,
        *args,
        **kwargs,
    ) -> CommandResult:
        self._collector.increment("attempts")
        result: CommandResult = next_handler(*args, **kwargs)
        if result.exit_code in self._success_codes:
            self._collector.increment("successes")
        else:
            self._collector.increment("failures")
            self._collector.increment("retries")
        return result

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def collector(self) -> MetricsCollector:
        return self._collector

    def reset(self) -> None:
        """Delegate a full reset to the underlying collector."""
        self._collector.reset()

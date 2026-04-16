"""Middleware that attaches a TagSet to each CommandResult as it passes
through the pipeline."""
from __future__ import annotations

from typing import Callable, Dict, Optional

from retryctl.runner import CommandResult
from retryctl.tag import TagSet


class TagMiddleware:
    """Injects static tags (and an optional dynamic resolver) into results.

    Parameters
    ----------
    tags:
        Static key/value pairs applied to every result.
    resolver:
        Optional callable ``(result) -> dict`` whose return value is merged
        after the static tags, allowing dynamic tagging based on outcome.
    """

    def __init__(
        self,
        tags: Optional[Dict[str, str]] = None,
        resolver: Optional[Callable[[CommandResult], Dict[str, str]]] = None,
    ) -> None:
        self._static: Dict[str, str] = dict(tags or {})
        self._resolver = resolver

    # ------------------------------------------------------------------
    def __call__(
        self,
        command: list,
        next_handler: Callable,
    ) -> CommandResult:
        result: CommandResult = next_handler(command)

        ts = TagSet()
        for k, v in self._static.items():
            ts.set(k, v)

        if self._resolver is not None:
            for k, v in self._resolver(result).items():
                ts.set(k, v)

        # Attach to result via a custom attribute so downstream consumers
        # (audit, metrics) can read it without coupling to this middleware.
        result.tags = ts  # type: ignore[attr-defined]
        return result

    # ------------------------------------------------------------------
    @property
    def static_tags(self) -> Dict[str, str]:
        return dict(self._static)

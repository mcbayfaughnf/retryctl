"""Correlation ID generation and propagation for retry runs."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CorrelationContext:
    """Holds a correlation ID and optional parent ID for a retry run."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None

    def child(self) -> "CorrelationContext":
        """Return a new context that is a child of this one."""
        return CorrelationContext(parent_id=self.run_id)

    def as_dict(self) -> dict:
        d = {"run_id": self.run_id}
        if self.parent_id is not None:
            d["parent_id"] = self.parent_id
        return d

    def __str__(self) -> str:
        if self.parent_id:
            return f"{self.parent_id}/{self.run_id}"
        return self.run_id


class CorrelationMiddleware:
    """Middleware that attaches a CorrelationContext to each CommandResult."""

    def __init__(self, context: Optional[CorrelationContext] = None) -> None:
        self._ctx = context or CorrelationContext()

    def __call__(self, command, config, next_fn):
        result = next_fn(command, config)
        if hasattr(result, "extra") and isinstance(result.extra, dict):
            result.extra["correlation"] = self._ctx.as_dict()
        return result

    @property
    def context(self) -> CorrelationContext:
        return self._ctx

    def reset(self, context: Optional[CorrelationContext] = None) -> None:
        """Replace the active context (useful between independent runs)."""
        self._ctx = context or CorrelationContext()

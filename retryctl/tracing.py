"""Lightweight span-based tracing for retry attempts."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.monotonic)
    end_time: Optional[float] = None
    attributes: dict = field(default_factory=dict)

    def finish(self) -> None:
        if self.end_time is None:
            self.end_time = time.monotonic()

    @property
    def duration(self) -> Optional[float]:
        if self.end_time is None:
            return None
        return self.end_time - self.start_time

    def set(self, key: str, value: object) -> None:
        self.attributes[key] = value

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "duration": self.duration,
            "attributes": dict(self.attributes),
        }


class Tracer:
    def __init__(self, trace_id: Optional[str] = None) -> None:
        self.trace_id: str = trace_id or uuid.uuid4().hex
        self._spans: List[Span] = []

    def start_span(self, name: str, parent_id: Optional[str] = None) -> Span:
        span = Span(name=name, trace_id=self.trace_id, parent_id=parent_id)
        self._spans.append(span)
        return span

    @property
    def spans(self) -> List[Span]:
        return list(self._spans)

    def finished_spans(self) -> List[Span]:
        return [s for s in self._spans if s.end_time is not None]

    def reset(self) -> None:
        self._spans.clear()

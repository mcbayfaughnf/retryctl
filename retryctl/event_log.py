"""Structured event log that records lifecycle events during a retry run."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class EventEntry:
    event: str
    attempt: int
    timestamp: float
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": self.event,
            "attempt": self.attempt,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class EventLog:
    """Append-only log of retry lifecycle events."""

    KNOWN_EVENTS = {"start", "attempt", "retry", "success", "failure", "cancelled"}

    def __init__(self) -> None:
        self._entries: List[EventEntry] = []

    def record(self, event: str, attempt: int, data: Optional[Dict[str, Any]] = None) -> EventEntry:
        if event not in self.KNOWN_EVENTS:
            raise ValueError(f"Unknown event '{event}'; expected one of {sorted(self.KNOWN_EVENTS)}")
        entry = EventEntry(
            event=event,
            attempt=attempt,
            timestamp=time.monotonic(),
            data=data or {},
        )
        self._entries.append(entry)
        return entry

    def entries(self) -> List[EventEntry]:
        return list(self._entries)

    def filter(self, event: str) -> List[EventEntry]:
        return [e for e in self._entries if e.event == event]

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)

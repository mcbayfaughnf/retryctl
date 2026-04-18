"""Priority queue for ordering retry attempts by urgency."""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any


class PriorityError(ValueError):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


@dataclass(order=True)
class PriorityEntry:
    priority: int
    sequence: int
    payload: Any = field(compare=False)

    def __repr__(self) -> str:
        return f"PriorityEntry(priority={self.priority}, sequence={self.sequence})"


@dataclass
class PriorityQueue:
    """Min-heap priority queue where lower priority value = higher urgency."""
    _heap: list = field(default_factory=list, init=False)
    _counter: int = field(default=0, init=False)

    def push(self, payload: Any, priority: int = 0) -> PriorityEntry:
        if priority < 0:
            raise PriorityError(f"priority must be >= 0, got {priority}")
        entry = PriorityEntry(priority=priority, sequence=self._counter, payload=payload)
        self._counter += 1
        heapq.heappush(self._heap, entry)
        return entry

    def pop(self) -> PriorityEntry:
        if not self._heap:
            raise IndexError("pop from empty PriorityQueue")
        return heapq.heappop(self._heap)

    def peek(self) -> PriorityEntry:
        if not self._heap:
            raise IndexError("peek at empty PriorityQueue")
        return self._heap[0]

    @property
    def size(self) -> int:
        return len(self._heap)

    def empty(self) -> bool:
        return self.size == 0

    def drain(self) -> list[PriorityEntry]:
        """Return all entries sorted by priority, clearing the queue."""
        result = []
        while self._heap:
            result.append(heapq.heappop(self._heap))
        return result

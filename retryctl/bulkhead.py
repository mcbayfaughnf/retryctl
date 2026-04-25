"""Bulkhead pattern: isolate failures by capping concurrent calls per named partition."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Semaphore
from typing import Dict


class BulkheadFull(Exception):
    """Raised when a bulkhead partition has no remaining capacity."""

    def __init__(self, name: str, limit: int) -> None:
        self.name = name
        self.limit = limit
        super().__init__(f"Bulkhead '{name}' is full (limit={limit})")


@dataclass
class BulkheadPartition:
    name: str
    limit: int
    _sem: Semaphore = field(init=False, repr=False)
    _active: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise ValueError(f"limit must be positive, got {self.limit}")
        self._sem = Semaphore(self.limit)

    @property
    def active(self) -> int:
        return self._active

    @property
    def available(self) -> int:
        return self.limit - self._active

    def acquire(self) -> None:
        acquired = self._sem.acquire(blocking=False)
        if not acquired:
            raise BulkheadFull(self.name, self.limit)
        self._active += 1

    def release(self) -> None:
        if self._active > 0:
            self._active -= 1
            self._sem.release()


_partitions: Dict[str, BulkheadPartition] = {}


def get_or_create(name: str, limit: int = 10) -> BulkheadPartition:
    if name not in _partitions:
        _partitions[name] = BulkheadPartition(name=name, limit=limit)
    return _partitions[name]


def get(name: str) -> BulkheadPartition:
    if name not in _partitions:
        raise KeyError(f"No bulkhead partition named '{name}'")
    return _partitions[name]


def remove(name: str) -> None:
    _partitions.pop(name, None)


def reset_all() -> None:
    _partitions.clear()

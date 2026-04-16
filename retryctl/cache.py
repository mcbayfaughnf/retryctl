"""Result caching for idempotent commands.

Provides a simple TTL-based cache so that a successful command result
can be replayed without re-executing the subprocess during a retry
window.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class CacheEntry:
    """A single cached command result."""

    stdout: str
    stderr: str
    returncode: int
    created_at: float = field(default_factory=time.monotonic)
    ttl: float = 60.0

    @property
    def expired(self) -> bool:
        return (time.monotonic() - self.created_at) > self.ttl

    @property
    def age(self) -> float:
        """Seconds elapsed since this entry was created."""
        return time.monotonic() - self.created_at

    @property
    def remaining_ttl(self) -> float:
        """Seconds until this entry expires (0.0 if already expired)."""
        return max(0.0, self.ttl - self.age)


class ResultCache:
    """In-memory TTL cache keyed by a hash of the command arguments."""

    def __init__(self, default_ttl: float = 60.0) -> None:
        if default_ttl <= 0:
            raise ValueError("default_ttl must be positive")
        self.default_ttl = default_ttl
        self._store: Dict[str, CacheEntry] = {}

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def key(self, command: list[str]) -> str:
        """Return a deterministic cache key for *command*."""
        raw = "\x00".join(command).encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, command: list[str]) -> Optional[CacheEntry]:
        """Return a non-expired entry or *None*."""
        entry = self._store.get(self.key(command))
        if entry is None or entry.expired:
            return None
        return entry

    def set(
        self,
        command: list[str],
        stdout: str,
        stderr: str,
        returncode: int,
        ttl: Optional[float] = None,
    ) -> CacheEntry:
        """Store a result and return the new entry."""
        entry = CacheEntry(
            stdout=stdout,
            stderr=stderr,
            returncode=returncode,
            ttl=ttl if ttl is not None else self.default_ttl,
        )
        self._store[self.key(command)] = entry
        return entry

    def invalidate(self, command: list[str]) -> bool:
        """Remove an entry; return *True* if it existed."""
        return self._store.pop(self.key(command), None) is not None

    def clear(self) -> None:
        """Evict all entries."""
        self._store.clear()

    def evict_expired(self) -> int:
        """Remove all expired entries and return the number evicted."""
        expired_keys = [k for k, v in self._store.items() if v.expired]
        for k in expired_keys:
            del self._store[k]
        return len(expired_keys)

    def __len__(self) -> int:
        return len(self._store)

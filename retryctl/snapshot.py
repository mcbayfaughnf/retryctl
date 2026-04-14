"""Snapshot: capture and compare command output across attempts."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OutputSnapshot:
    """Immutable record of a single attempt's stdout/stderr."""

    attempt: int
    stdout: str
    stderr: str
    exit_code: int
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        raw = f"{self.stdout}\x00{self.stderr}\x00{self.exit_code}"
        self.digest = hashlib.sha256(raw.encode()).hexdigest()

    def matches(self, other: "OutputSnapshot") -> bool:
        """Return True when both snapshots have identical output and exit code."""
        return self.digest == other.digest


@dataclass
class SnapshotHistory:
    """Ordered log of OutputSnapshots for a single run."""

    _entries: List[OutputSnapshot] = field(default_factory=list, init=False)

    def record(self, snapshot: OutputSnapshot) -> None:
        self._entries.append(snapshot)

    def latest(self) -> Optional[OutputSnapshot]:
        return self._entries[-1] if self._entries else None

    def previous(self) -> Optional[OutputSnapshot]:
        return self._entries[-2] if len(self._entries) >= 2 else None

    def output_changed(self) -> bool:
        """Return True when the two most recent snapshots differ."""
        prev, curr = self.previous(), self.latest()
        if prev is None or curr is None:
            return False
        return not prev.matches(curr)

    def all(self) -> List[OutputSnapshot]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

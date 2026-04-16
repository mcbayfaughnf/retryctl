"""Checkpoint support – persist attempt progress so a run can be resumed."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class CheckpointData:
    command: str
    attempt: int
    last_exit_code: Optional[int]
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "CheckpointData":
        return CheckpointData(
            command=d["command"],
            attempt=d["attempt"],
            last_exit_code=d.get("last_exit_code"),
            started_at=d.get("started_at", 0.0),
            updated_at=d.get("updated_at", 0.0),
        )


class CheckpointStore:
    """Read/write checkpoint files as JSON."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    # ------------------------------------------------------------------
    def save(self, data: CheckpointData) -> None:
        data.updated_at = time.time()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data.to_dict(), indent=2))
        tmp.replace(self._path)

    def load(self) -> Optional[CheckpointData]:
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text())
            return CheckpointData.from_dict(raw)
        except (json.JSONDecodeError, KeyError):
            return None

    def clear(self) -> None:
        if self._path.exists():
            os.remove(self._path)

    @property
    def exists(self) -> bool:
        return self._path.exists()

"""Audit log: writes a structured JSONL record for every completed run."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from retryctl.reporter import RunSummary


@dataclass
class AuditEntry:
    """One line in the audit log."""

    timestamp: str
    command: list[str]
    exit_code: int
    attempts: int
    total_duration: float
    succeeded: bool
    log_path: str = ""
    extra: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_entry(summary: RunSummary, extra: Optional[dict] = None) -> AuditEntry:
    """Convert a *RunSummary* into an *AuditEntry*."""
    last = summary.attempts[-1] if summary.attempts else None
    exit_code = last.result.exit_code if last else -1
    command = list(last.result.command) if last else []
    return AuditEntry(
        timestamp=_utcnow(),
        command=command,
        exit_code=exit_code,
        attempts=len(summary.attempts),
        total_duration=round(summary.total_duration, 4),
        succeeded=summary.succeeded,
        extra=extra or {},
    )


class AuditLogger:
    """Appends JSONL audit entries to *path*."""

    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> Path:
        return self._path

    def write(self, entry: AuditEntry) -> None:
        """Append *entry* as a single JSON line."""
        entry.log_path = str(self._path)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(entry.to_json() + "\n")

    def log_summary(self, summary: RunSummary, extra: Optional[dict] = None) -> AuditEntry:
        """Build an entry from *summary*, write it, and return it."""
        entry = build_entry(summary, extra=extra)
        self.write(entry)
        return entry

    def read_entries(self) -> list[AuditEntry]:
        """Read and parse all entries from the audit log.

        Returns an empty list if the log file does not exist yet.
        Raises ``json.JSONDecodeError`` if a line contains malformed JSON.
        """
        if not self._path.exists():
            return []
        entries = []
        with self._path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise json.JSONDecodeError(
                        f"Malformed JSON on line {lineno} of {self._path}: {exc.msg}",
                        exc.doc,
                        exc.pos,
                    ) from exc
                entries.append(AuditEntry(**data))
        return entries

"""Manifest: snapshot of the active middleware pipeline configuration."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ManifestEntry:
    """Describes a single middleware layer in the pipeline."""

    name: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "enabled": self.enabled, "params": self.params}


@dataclass
class Manifest:
    """Immutable snapshot of the pipeline configuration."""

    version: str = "1"
    entries: list[ManifestEntry] = field(default_factory=list)

    # ------------------------------------------------------------------
    def add(self, entry: ManifestEntry) -> None:
        """Append a middleware entry to the manifest."""
        self.entries.append(entry)

    def remove(self, name: str) -> bool:
        """Remove the first entry whose name matches; return True if found."""
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.name != name]
        return len(self.entries) < before

    def get(self, name: str) -> ManifestEntry | None:
        """Return the first entry with the given name, or None."""
        return next((e for e in self.entries if e.name == name), None)

    def enabled_names(self) -> list[str]:
        """Return names of all enabled middleware layers."""
        return [e.name for e in self.entries if e.enabled]

    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {"version": self.version, "entries": [e.to_dict() for e in self.entries]}

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        entries = [
            ManifestEntry(
                name=e["name"],
                enabled=e.get("enabled", True),
                params=e.get("params", {}),
            )
            for e in data.get("entries", [])
        ]
        return cls(version=data.get("version", "1"), entries=entries)

    @classmethod
    def from_json(cls, text: str) -> "Manifest":
        return cls.from_dict(json.loads(text))

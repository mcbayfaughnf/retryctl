"""Structured label tagging for retry runs.

Labels are arbitrary key=value string pairs attached to a run, useful for
filtering audit logs, metrics, or distinguishing named workflows.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

_KEY_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_.-]*$')
_MAX_VALUE_LEN = 256


class LabelError(ValueError):
    """Raised when a label key or value is invalid."""


@dataclass
class LabelSet:
    """An immutable-ish collection of string labels."""

    _labels: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def add(self, key: str, value: str) -> None:
        """Add or overwrite a label after validating key and value."""
        if not _KEY_RE.match(key):
            raise LabelError(
                f"Invalid label key {key!r}: must match [a-zA-Z_][a-zA-Z0-9_.-]*"
            )
        if len(value) > _MAX_VALUE_LEN:
            raise LabelError(
                f"Label value for {key!r} exceeds maximum length of {_MAX_VALUE_LEN}"
            )
        self._labels[key] = value

    def remove(self, key: str) -> None:
        """Remove a label; silently ignores missing keys."""
        self._labels.pop(key, None)

    def get(self, key: str) -> Optional[str]:
        """Return the value for *key*, or None if absent."""
        return self._labels.get(key)

    def as_dict(self) -> Dict[str, str]:
        """Return a shallow copy of the underlying label mapping."""
        return dict(self._labels)

    def __len__(self) -> int:
        return len(self._labels)

    def __contains__(self, key: object) -> bool:
        return key in self._labels

    def __repr__(self) -> str:  # pragma: no cover
        return f"LabelSet({self._labels!r})"


def parse_labels(pairs: Iterable[str]) -> LabelSet:
    """Parse an iterable of ``key=value`` strings into a :class:`LabelSet`.

    Raises :class:`LabelError` if any string is not in ``key=value`` format.
    """
    ls = LabelSet()
    for pair in pairs:
        if '=' not in pair:
            raise LabelError(
                f"Label {pair!r} is not in key=value format"
            )
        key, _, value = pair.partition('=')
        ls.add(key, value)
    return ls

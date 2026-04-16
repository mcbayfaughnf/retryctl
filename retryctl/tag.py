"""Attempt tagging — attach arbitrary key/value tags to each attempt for
downstream consumers (audit, metrics, reporters)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional

_KEY_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_.\-]*$')
_MAX_VALUE_LEN = 256


class TagError(ValueError):
    """Raised for invalid tag keys or values."""


@dataclass
class TagSet:
    """Immutable-ish collection of string tags attached to a retry attempt."""
    _tags: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def set(self, key: str, value: str) -> None:
        """Add or overwrite a tag."""
        if not _KEY_RE.match(key):
            raise TagError(f"Invalid tag key: {key!r}")
        if len(value) > _MAX_VALUE_LEN:
            raise TagError(
                f"Tag value for {key!r} exceeds {_MAX_VALUE_LEN} characters"
            )
        self._tags[key] = value

    def remove(self, key: str) -> None:
        """Remove a tag; silently ignores missing keys."""
        self._tags.pop(key, None)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self._tags.get(key, default)

    def all(self) -> Dict[str, str]:
        return dict(self._tags)

    def __iter__(self) -> Iterator[str]:
        return iter(self._tags)

    def __len__(self) -> int:
        return len(self._tags)

    def __contains__(self, key: object) -> bool:
        return key in self._tags

    def __repr__(self) -> str:  # pragma: no cover
        return f"TagSet({self._tags!r})"

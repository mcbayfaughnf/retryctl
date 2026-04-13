"""Output formatting utilities for retryctl run results."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from retryctl.runner import CommandResult


def format_text(result: "CommandResult") -> str:
    """Return a human-readable summary of a CommandResult."""
    lines = [
        f"command   : {' '.join(result.command)}",
        f"exit code : {result.returncode}",
        f"attempts  : {result.attempts}",
        f"succeeded : {result.succeeded}",
        f"elapsed   : {result.elapsed:.3f}s",
    ]
    if result.stdout:
        lines.append(f"stdout    :\n{result.stdout.rstrip()}")
    if result.stderr:
        lines.append(f"stderr    :\n{result.stderr.rstrip()}")
    return "\n".join(lines)


def format_json(result: "CommandResult") -> str:
    """Return a JSON-encoded summary of a CommandResult."""
    payload = {
        "command": list(result.command),
        "returncode": result.returncode,
        "attempts": result.attempts,
        "succeeded": result.succeeded,
        "elapsed": round(result.elapsed, 6),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    return json.dumps(payload, indent=2)


_FORMATS = {
    "text": format_text,
    "json": format_json,
}


def get_formatter(fmt: str):
    """Return a formatter callable for *fmt* (``'text'`` or ``'json'``).

    Raises
    ------
    ValueError
        If *fmt* is not a recognised format name.
    """
    try:
        return _FORMATS[fmt]
    except KeyError:
        valid = ", ".join(sorted(_FORMATS))
        raise ValueError(f"Unknown output format {fmt!r}. Choose from: {valid}")


AVAILABLE_FORMATS: list[str] = list(_FORMATS.keys())

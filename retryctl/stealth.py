"""Stealth mode: suppress stdout/stderr output on successful attempts.

When enabled, output from the wrapped command is buffered and only
released if the attempt ultimately fails (or the run exhausts all
retries).  On a clean success the output is silently discarded.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from retryctl.runner import CommandResult


@dataclass
class StealthConfig:
    """Configuration for stealth-mode output suppression."""

    suppress_stdout: bool = True
    suppress_stderr: bool = True
    # If True, buffered output is printed to the *real* streams on failure.
    release_on_failure: bool = True

    def __post_init__(self) -> None:
        if not self.suppress_stdout and not self.suppress_stderr:
            raise ValueError(
                "StealthConfig: at least one of suppress_stdout or "
                "suppress_stderr must be True"
            )


@dataclass
class StealthBuffer:
    """Accumulates per-attempt output lines."""

    _stdout_lines: List[str] = field(default_factory=list)
    _stderr_lines: List[str] = field(default_factory=list)

    def record(self, result: CommandResult) -> None:
        """Buffer the stdout/stderr captured in *result*."""
        if result.stdout:
            self._stdout_lines.append(result.stdout)
        if result.stderr:
            self._stderr_lines.append(result.stderr)

    def release(self) -> None:
        """Flush buffered output to the real streams."""
        for chunk in self._stdout_lines:
            sys.stdout.write(chunk)
        for chunk in self._stderr_lines:
            sys.stderr.write(chunk)
        sys.stdout.flush()
        sys.stderr.flush()

    def clear(self) -> None:
        """Discard all buffered output."""
        self._stdout_lines.clear()
        self._stderr_lines.clear()

    @property
    def stdout_captured(self) -> str:
        return "".join(self._stdout_lines)

    @property
    def stderr_captured(self) -> str:
        return "".join(self._stderr_lines)


class StealthMiddleware:
    """Middleware that suppresses command output on success."""

    def __init__(
        self,
        config: Optional[StealthConfig] = None,
    ) -> None:
        self._config = config or StealthConfig()
        self._buffer = StealthBuffer()

    def __call__(
        self,
        next_fn: Callable[..., CommandResult],
        *args,
        **kwargs,
    ) -> CommandResult:
        result: CommandResult = next_fn(*args, **kwargs)
        self._buffer.record(result)

        if result.exit_code == 0:
            # Success — silently discard buffered output.
            self._buffer.clear()
        else:
            if self._config.release_on_failure:
                self._buffer.release()
            self._buffer.clear()

        return result

    def reset(self) -> None:
        """Clear the internal buffer (useful between independent runs)."""
        self._buffer.clear()

    @property
    def buffer(self) -> StealthBuffer:
        return self._buffer

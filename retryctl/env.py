"""Environment variable injection for retry context.

Exposes retry metadata (attempt number, max attempts, last exit code, etc.)
as environment variables so that wrapped commands can inspect retry state.
"""
from __future__ import annotations

import os
from typing import Dict, Optional


# Prefix used for all injected variables.
ENV_PREFIX = "RETRYCTL_"


def build_env(
    attempt: int,
    max_attempts: int,
    last_exit_code: Optional[int],
    command: str,
    base: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Return an environment dict that merges *base* with retry metadata.

    Args:
        attempt:        1-based index of the current attempt.
        max_attempts:   Total number of attempts allowed (0 = unlimited).
        last_exit_code: Exit code from the previous attempt, or ``None`` on the
                        first attempt.
        command:        The command string being executed.
        base:           Starting environment; defaults to ``os.environ``.

    Returns:
        A new ``dict`` suitable for passing to ``subprocess`` as *env*.
    """
    env = dict(os.environ if base is None else base)

    env[f"{ENV_PREFIX}ATTEMPT"] = str(attempt)
    env[f"{ENV_PREFIX}MAX_ATTEMPTS"] = str(max_attempts)
    env[f"{ENV_PREFIX}COMMAND"] = command
    env[f"{ENV_PREFIX}LAST_EXIT_CODE"] = (
        str(last_exit_code) if last_exit_code is not None else ""
    )
    return env


def strip_env(env: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of *env* with all ``RETRYCTL_*`` keys removed."""
    return {k: v for k, v in env.items() if not k.startswith(ENV_PREFIX)}


def current_attempt(env: Optional[Dict[str, str]] = None) -> Optional[int]:
    """Read ``RETRYCTL_ATTEMPT`` from *env* (or ``os.environ``) if present."""
    source = env if env is not None else os.environ
    raw = source.get(f"{ENV_PREFIX}ATTEMPT")
    return int(raw) if raw is not None else None

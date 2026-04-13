"""Command runner with retry logic."""

import subprocess
import time
import sys
from typing import Optional

from retryctl.config import RetryConfig
from retryctl.backoff import get_backoff_sequence


class CommandResult:
    """Result of a command execution attempt."""

    def __init__(self, returncode: int, stdout: str, stderr: str, attempts: int):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.attempts = attempts
        self.succeeded = returncode == 0

    def __repr__(self) -> str:
        return (
            f"CommandResult(returncode={self.returncode}, "
            f"attempts={self.attempts}, succeeded={self.succeeded})"
        )


def run_command(
    command: list[str],
    config: RetryConfig,
    verbose: bool = False,
) -> CommandResult:
    """Run a command with retry logic based on the provided config."""
    backoff_gen = get_backoff_sequence(config)
    last_result: Optional[subprocess.CompletedProcess] = None

    for attempt in range(1, config.max_attempts + 1):
        if verbose:
            print(f"[retryctl] Attempt {attempt}/{config.max_attempts}: {' '.join(command)}", file=sys.stderr)

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=config.timeout,
            )
        except subprocess.TimeoutExpired:
            if verbose:
                print(f"[retryctl] Attempt {attempt} timed out.", file=sys.stderr)
            last_result = None
            if attempt < config.max_attempts:
                delay = next(backoff_gen)
                if verbose:
                    print(f"[retryctl] Waiting {delay:.2f}s before next attempt...", file=sys.stderr)
                time.sleep(delay)
            continue

        last_result = result

        if result.returncode == 0:
            return CommandResult(
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                attempts=attempt,
            )

        if verbose:
            print(f"[retryctl] Attempt {attempt} failed with exit code {result.returncode}.", file=sys.stderr)

        if attempt < config.max_attempts:
            delay = next(backoff_gen)
            if verbose:
                print(f"[retryctl] Waiting {delay:.2f}s before next attempt...", file=sys.stderr)
            time.sleep(delay)

    if last_result is not None:
        return CommandResult(
            returncode=last_result.returncode,
            stdout=last_result.stdout,
            stderr=last_result.stderr,
            attempts=config.max_attempts,
        )

    return CommandResult(returncode=1, stdout="", stderr="Command timed out on all attempts.", attempts=config.max_attempts)

"""CLI entry point for retryctl."""

import sys
import argparse

from retryctl.config import RetryConfig
from retryctl.runner import run_command
from retryctl.backoff import BackoffStrategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="retryctl",
        description="Run a command with configurable retry and backoff logic.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run")
    parser.add_argument("-n", "--max-attempts", type=int, default=3, help="Maximum number of attempts (default: 3)")
    parser.add_argument("-d", "--delay", type=float, default=1.0, help="Initial delay in seconds (default: 1.0)")
    parser.add_argument(
        "-s",
        "--strategy",
        choices=[s.value for s in BackoffStrategy],
        default=BackoffStrategy.FIXED.value,
        help="Backoff strategy (default: fixed)",
    )
    parser.add_argument("--multiplier", type=float, default=2.0, help="Multiplier for exponential/jitter backoff")
    parser.add_argument("--increment", type=float, default=1.0, help="Increment for linear backoff")
    parser.add_argument("--max-delay", type=float, default=60.0, help="Maximum delay between retries (default: 60)")
    parser.add_argument("--timeout", type=float, default=None, help="Timeout per attempt in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print retry info to stderr")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    command = [c for c in args.command if c != "--"]
    if not command:
        parser.error("No command specified.")

    config = RetryConfig(
        max_attempts=args.max_attempts,
        backoff_strategy=args.strategy,
        initial_delay=args.delay,
        max_delay=args.max_delay,
        multiplier=args.multiplier,
        increment=args.increment,
        timeout=args.timeout,
    )

    result = run_command(command, config, verbose=args.verbose)

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

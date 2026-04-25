"""Scatter-gather middleware: fan out a command to N parallel lanes and
collect results, succeeding when *quorum* lanes succeed."""
from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from retryctl.runner import CommandResult


class ScatterError(Exception):
    """Raised when fewer than *quorum* lanes succeed."""

    def __init__(self, succeeded: int, quorum: int, total: int) -> None:
        self.succeeded = succeeded
        self.quorum = quorum
        self.total = total
        super().__init__(
            f"scatter quorum not met: {succeeded}/{total} succeeded, "
            f"required {quorum}"
        )


@dataclass
class ScatterPolicy:
    lanes: int = 3
    quorum: int = 2
    timeout: Optional[float] = None

    def __post_init__(self) -> None:
        if self.lanes < 1:
            raise ValueError("lanes must be >= 1")
        if self.quorum < 1:
            raise ValueError("quorum must be >= 1")
        if self.quorum > self.lanes:
            raise ValueError("quorum cannot exceed lanes")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class ScatterResult:
    """Aggregated outcome from a scatter run."""
    results: List[CommandResult] = field(default_factory=list)
    succeeded: int = 0
    failed: int = 0

    @property
    def best(self) -> Optional[CommandResult]:
        """Return the first successful result, or the first result overall."""
        for r in self.results:
            if r.exit_code == 0:
                return r
        return self.results[0] if self.results else None


class ScatterMiddleware:
    """Fan the command out across *policy.lanes* threads and require
    *policy.quorum* successes before returning.
    """

    def __init__(self, policy: Optional[ScatterPolicy] = None) -> None:
        self._policy = policy or ScatterPolicy()

    def __call__(
        self, next_fn: Callable[..., CommandResult], *args, **kwargs
    ) -> CommandResult:
        policy = self._policy
        scatter_result = ScatterResult()

        with concurrent.futures.ThreadPoolExecutor(max_workers=policy.lanes) as ex:
            futures = [
                ex.submit(next_fn, *args, **kwargs)
                for _ in range(policy.lanes)
            ]
            done, _ = concurrent.futures.wait(
                futures,
                timeout=policy.timeout,
                return_when=concurrent.futures.ALL_COMPLETED,
            )

        for fut in done:
            try:
                res: CommandResult = fut.result()
                scatter_result.results.append(res)
                if res.exit_code == 0:
                    scatter_result.succeeded += 1
                else:
                    scatter_result.failed += 1
            except Exception:
                scatter_result.failed += 1

        if scatter_result.succeeded < policy.quorum:
            raise ScatterError(
                scatter_result.succeeded, policy.quorum, policy.lanes
            )

        return scatter_result.best  # type: ignore[return-value]

    @property
    def policy(self) -> ScatterPolicy:
        return self._policy

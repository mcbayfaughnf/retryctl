"""Middleware that short-circuits execution using a ResultCache.

When a cached (and non-expired) result exists for the command being
executed the middleware returns it immediately, skipping the real
subprocess call.  On a successful run the result is stored so that
subsequent retries within the TTL window are free.
"""

from __future__ import annotations

from typing import Callable, Optional

from retryctl.cache import ResultCache
from retryctl.runner import CommandResult

# Type alias matching MiddlewarePipeline's expected callable signature.
_Handler = Callable[[list[str]], CommandResult]


class CacheMiddleware:
    """Wraps a command handler with read-through / write-through caching."""

    def __init__(
        self,
        cache: Optional[ResultCache] = None,
        *,
        ttl: float = 60.0,
        cache_failures: bool = False,
    ) -> None:
        self._cache = cache if cache is not None else ResultCache(default_ttl=ttl)
        self._ttl = ttl
        self._cache_failures = cache_failures

    # ------------------------------------------------------------------
    # callable interface
    # ------------------------------------------------------------------

    def __call__(self, command: list[str], next_handler: _Handler) -> CommandResult:
        """Return a cached result or delegate to *next_handler*."""
        entry = self._cache.get(command)
        if entry is not None:
            return CommandResult(
                command=command,
                returncode=entry.returncode,
                stdout=entry.stdout,
                stderr=entry.stderr,
                attempts=1,
                from_cache=True,
            )

        result: CommandResult = next_handler(command)

        should_cache = result.returncode == 0 or self._cache_failures
        if should_cache:
            self._cache.set(
                command,
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
                ttl=self._ttl,
            )

        return result

    # ------------------------------------------------------------------
    # convenience
    # ------------------------------------------------------------------

    def invalidate(self, command: list[str]) -> bool:
        """Manually remove *command* from the cache."""
        return self._cache.invalidate(command)

    def clear(self) -> None:
        """Flush the entire cache."""
        self._cache.clear()

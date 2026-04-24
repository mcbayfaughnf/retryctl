"""Convenience helpers to attach FallbackMiddleware to a MiddlewarePipeline."""
from __future__ import annotations

from typing import Sequence

from retryctl.fallback import FallbackMiddleware, FallbackPolicy
from retryctl.fallback_registry import get_or_create
from retryctl.middleware import MiddlewarePipeline


def attach_fallback(
    pipeline: MiddlewarePipeline,
    *,
    name: str,
    command: Sequence[str],
    on_exit_codes: Sequence[int] = (),
    on_any_failure: bool = False,
) -> FallbackMiddleware:
    """Create (or reuse) a named FallbackPolicy and attach it to *pipeline*.

    Returns the :class:`FallbackMiddleware` instance so callers can inspect
    ``last_fallback`` after execution.
    """
    policy = get_or_create(
        name,
        command,
        on_exit_codes=on_exit_codes,
        on_any_failure=on_any_failure,
    )
    mw = FallbackMiddleware(policy)
    pipeline.add(mw)
    return mw


def attach_fallback_from_policy(
    pipeline: MiddlewarePipeline,
    policy: FallbackPolicy,
) -> FallbackMiddleware:
    """Attach a pre-built *policy* to *pipeline* and return the middleware."""
    mw = FallbackMiddleware(policy)
    pipeline.add(mw)
    return mw


def build_fallback_pipeline(
    *,
    fallback_command: Sequence[str],
    on_exit_codes: Sequence[int] = (),
    on_any_failure: bool = False,
) -> tuple[MiddlewarePipeline, FallbackMiddleware]:
    """Return a fresh pipeline with a single FallbackMiddleware pre-attached.

    Useful for simple single-command setups in tests or CLI integration.
    """
    policy = FallbackPolicy(
        command=list(fallback_command),
        on_exit_codes=list(on_exit_codes),
        on_any_failure=on_any_failure,
    )
    pipeline = MiddlewarePipeline()
    mw = attach_fallback_from_policy(pipeline, policy)
    return pipeline, mw

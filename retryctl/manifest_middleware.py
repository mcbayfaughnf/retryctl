"""ManifestMiddleware: enforces that only enabled pipeline layers may run."""
from __future__ import annotations

from typing import Callable

from retryctl.manifest import Manifest
from retryctl.runner import CommandResult


class ManifestMiddleware:
    """Gate middleware execution based on a Manifest.

    If the middleware *name* is present in the manifest but disabled, the
    call is forwarded directly to *next* without running the wrapped layer.
    If the name is absent from the manifest the call is also forwarded
    (opt-in-only mode is the default; pass ``strict=True`` to block unknown
    names instead).
    """

    def __init__(
        self,
        name: str,
        manifest: Manifest,
        inner: Callable[..., CommandResult],
        *,
        strict: bool = False,
    ) -> None:
        if not name:
            raise ValueError("name must be a non-empty string")
        self._name = name
        self._manifest = manifest
        self._inner = inner
        self._strict = strict

    # ------------------------------------------------------------------
    @property
    def name(self) -> str:
        return self._name

    @property
    def manifest(self) -> Manifest:
        return self._manifest

    # ------------------------------------------------------------------
    def __call__(self, next_fn: Callable[..., CommandResult], *args, **kwargs) -> CommandResult:
        entry = self._manifest.get(self._name)

        if entry is None:
            if self._strict:
                raise PermissionError(
                    f"Middleware '{self._name}' is not registered in the manifest"
                )
            # Unknown but not strict — pass through
            return next_fn(*args, **kwargs)

        if not entry.enabled:
            # Skip the inner layer entirely
            return next_fn(*args, **kwargs)

        return self._inner(next_fn, *args, **kwargs)

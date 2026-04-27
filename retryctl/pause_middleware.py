"""Middleware that checks a PauseController before each attempt."""
from __future__ import annotations

from typing import Callable

from retryctl.pause import PauseController, PausePolicy
from retryctl.runner import CommandResult


class PauseMiddleware:
    """Intercept each attempt and block while the controller is paused.

    Parameters
    ----------
    controller:
        Shared :class:`PauseController` instance.  If *None* a new
        controller with default policy is created.
    policy:
        :class:`PausePolicy` forwarded to the controller when *controller*
        is *None*.
    """

    def __init__(
        self,
        controller: PauseController | None = None,
        policy: PausePolicy | None = None,
    ) -> None:
        self._controller = controller or PauseController(policy)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def controller(self) -> PauseController:
        return self._controller

    def pause(self) -> None:
        """Convenience proxy to the underlying controller."""
        self._controller.pause()

    def resume(self) -> None:
        """Convenience proxy to the underlying controller."""
        self._controller.resume()

    # ------------------------------------------------------------------
    # Middleware protocol
    # ------------------------------------------------------------------

    def __call__(
        self,
        next_fn: Callable[..., CommandResult],
        *args: object,
        **kwargs: object,
    ) -> CommandResult:
        self._controller.wait_if_paused()
        return next_fn(*args, **kwargs)

"""Signal/event bus for retryctl lifecycle events.

Provides a lightweight pub/sub mechanism so that independent components
(hooks, reporter, formatter) can react to retry lifecycle events without
being tightly coupled to the runner.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, Dict, List

# Type alias for subscriber callbacks
Handler = Callable[..., None]

# Well-known event names
EVENT_START = "start"
EVENT_RETRY = "retry"
EVENT_SUCCESS = "success"
EVENT_FAILURE = "failure"

_KNOWN_EVENTS = {EVENT_START, EVENT_RETRY, EVENT_SUCCESS, EVENT_FAILURE}


class SignalBus:
    """A simple synchronous event bus."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[Handler]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def on(self, event: str, handler: Handler) -> None:
        """Register *handler* to be called when *event* is emitted."""
        if event not in _KNOWN_EVENTS:
            raise ValueError(
                f"Unknown event {event!r}. Known events: {sorted(_KNOWN_EVENTS)}"
            )
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Handler) -> None:
        """Unregister a previously registered *handler* for *event*."""
        try:
            self._handlers[event].remove(handler)
        except ValueError:
            pass

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------

    def emit(self, event: str, **kwargs: Any) -> None:
        """Call all handlers registered for *event*, passing **kwargs**."""
        for handler in list(self._handlers.get(event, [])):
            handler(**kwargs)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def handler_count(self, event: str) -> int:
        """Return the number of handlers registered for *event*."""
        return len(self._handlers.get(event, []))

    def clear(self, event: str | None = None) -> None:
        """Remove all handlers for *event*, or all handlers if *event* is None."""
        if event is None:
            self._handlers.clear()
        else:
            self._handlers.pop(event, None)


# Module-level default bus so callers can use `signals.bus` directly.
bus: SignalBus = SignalBus()

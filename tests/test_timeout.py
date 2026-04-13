"""Tests for retryctl.timeout."""
from __future__ import annotations

import time
import pytest

from retryctl.timeout import TimeoutExpired, remaining, timeout_context


# ---------------------------------------------------------------------------
# TimeoutExpired
# ---------------------------------------------------------------------------

class TestTimeoutExpired:
    def test_message_contains_seconds(self) -> None:
        exc = TimeoutExpired(5.0)
        assert "5.0" in str(exc)

    def test_message_contains_scope(self) -> None:
        exc = TimeoutExpired(3.0, scope="overall")
        assert "overall" in str(exc)

    def test_default_scope_is_attempt(self) -> None:
        exc = TimeoutExpired(1.0)
        assert exc.scope == "attempt"

    def test_stores_seconds(self) -> None:
        exc = TimeoutExpired(7.5)
        assert exc.seconds == 7.5


# ---------------------------------------------------------------------------
# timeout_context
# ---------------------------------------------------------------------------

class TestTimeoutContext:
    def test_noop_when_seconds_is_none(self) -> None:
        with timeout_context(None):
            time.sleep(0.01)  # should not raise

    def test_noop_when_seconds_is_zero(self) -> None:
        with timeout_context(0):
            time.sleep(0.01)  # should not raise

    def test_raises_on_expiry(self) -> None:
        with pytest.raises(TimeoutExpired) as exc_info:
            with timeout_context(0.05, scope="attempt"):
                time.sleep(1.0)
        assert exc_info.value.scope == "attempt"
        assert exc_info.value.seconds == 0.05

    def test_does_not_raise_when_within_limit(self) -> None:
        with timeout_context(2.0):
            time.sleep(0.01)  # well within limit

    def test_restores_previous_alarm_after_success(self) -> None:
        import signal
        if not hasattr(signal, "SIGALRM"):
            pytest.skip("SIGALRM not available")
        with timeout_context(2.0):
            pass
        # After context exits the itimer should be cleared
        remaining_alarm = signal.getitimer(signal.ITIMER_REAL)[0]
        assert remaining_alarm == 0.0


# ---------------------------------------------------------------------------
# remaining
# ---------------------------------------------------------------------------

class TestRemaining:
    def test_returns_none_when_no_deadline(self) -> None:
        assert remaining(None, 10.0) is None

    def test_returns_positive_seconds_left(self) -> None:
        result = remaining(30.0, 10.0)
        assert result == pytest.approx(20.0)

    def test_returns_zero_when_deadline_passed(self) -> None:
        result = remaining(5.0, 10.0)
        assert result == 0.0

    def test_returns_zero_exactly_at_deadline(self) -> None:
        result = remaining(5.0, 5.0)
        assert result == 0.0

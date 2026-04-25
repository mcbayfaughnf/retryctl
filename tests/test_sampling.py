"""Tests for retryctl.sampling."""
from __future__ import annotations

import pytest

from retryctl.runner import CommandResult
from retryctl.sampling import SampleSkipped, SamplingMiddleware, SamplingPolicy


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _result(exit_code: int = 0) -> CommandResult:
    return CommandResult(command="echo hi", exit_code=exit_code, stdout="hi", stderr="", attempts=1)


def _next(result: CommandResult):
    def handler(*args, **kwargs):
        return result
    return handler


# ---------------------------------------------------------------------------
# SamplingPolicy
# ---------------------------------------------------------------------------

class TestSamplingPolicyInit:
    def test_default_rate_is_one(self):
        p = SamplingPolicy()
        assert p.rate == 1.0

    def test_valid_rate_accepted(self):
        p = SamplingPolicy(rate=0.5)
        assert p.rate == 0.5

    def test_rate_above_one_raises(self):
        with pytest.raises(ValueError, match="rate"):
            SamplingPolicy(rate=1.1)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="rate"):
            SamplingPolicy(rate=-0.1)

    def test_zero_rate_accepted(self):
        p = SamplingPolicy(rate=0.0)
        assert p.rate == 0.0


class TestSamplingPolicyShouldSample:
    def test_rate_one_always_samples(self):
        p = SamplingPolicy(rate=1.0)
        assert all(p.should_sample(i) for i in range(1, 11))

    def test_rate_zero_never_samples(self):
        p = SamplingPolicy(rate=0.0)
        assert not any(p.should_sample(i) for i in range(1, 11))

    def test_skip_first_false_attempt_one_may_be_skipped(self):
        import random
        rng = random.Random(0)
        p = SamplingPolicy(rate=0.0, skip_first=False)
        # rate=0 means never sample regardless
        assert not p.should_sample(1, rng)

    def test_skip_first_true_always_forwards_attempt_one(self):
        p = SamplingPolicy(rate=0.0, skip_first=True)
        assert p.should_sample(1) is True

    def test_skip_first_true_still_samples_later_attempts_by_rate(self):
        p = SamplingPolicy(rate=0.0, skip_first=True)
        assert not p.should_sample(2)


# ---------------------------------------------------------------------------
# SamplingMiddleware
# ---------------------------------------------------------------------------

class TestSamplingMiddlewareSuccess:
    def test_delegates_to_next_when_sampled(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=1.0))
        r = _result()
        out = m(_next(r))
        assert out is r

    def test_increments_attempt_count(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=1.0))
        m(_next(_result()))
        m(_next(_result()))
        assert m.attempt_count == 2

    def test_skipped_count_zero_when_all_sampled(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=1.0))
        m(_next(_result()))
        assert m.skipped_count == 0


class TestSamplingMiddlewareSkip:
    def test_raises_sample_skipped_when_not_sampled(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=0.0))
        with pytest.raises(SampleSkipped):
            m(_next(_result()))

    def test_skipped_count_increments(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=0.0))
        for _ in range(3):
            with pytest.raises(SampleSkipped):
                m(_next(_result()))
        assert m.skipped_count == 3

    def test_sample_skipped_stores_rate_and_attempt(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=0.0))
        with pytest.raises(SampleSkipped) as exc_info:
            m(_next(_result()))
        err = exc_info.value
        assert err.rate == 0.0
        assert err.attempt == 1

    def test_sample_skipped_message_contains_attempt(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=0.0))
        with pytest.raises(SampleSkipped) as exc_info:
            m(_next(_result()))
        assert "attempt 1" in str(exc_info.value)


class TestSamplingMiddlewareReset:
    def test_reset_clears_counts(self):
        m = SamplingMiddleware(policy=SamplingPolicy(rate=1.0))
        m(_next(_result()))
        m.reset()
        assert m.attempt_count == 0
        assert m.skipped_count == 0

    def test_seed_makes_behaviour_deterministic(self):
        policy = SamplingPolicy(rate=0.5)
        m1 = SamplingMiddleware(policy=policy)
        m2 = SamplingMiddleware(policy=policy)
        m1.seed(42)
        m2.seed(42)
        results1, results2 = [], []
        for _ in range(10):
            try:
                m1(_next(_result()))
                results1.append(True)
            except SampleSkipped:
                results1.append(False)
            try:
                m2(_next(_result()))
                results2.append(True)
            except SampleSkipped:
                results2.append(False)
        assert results1 == results2

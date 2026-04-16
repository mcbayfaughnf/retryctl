"""Tests for retryctl.tracing."""
import time
import pytest
from retryctl.tracing import Span, Tracer


def _tracer() -> Tracer:
    return Tracer()


class TestSpan:
    def test_has_unique_span_id(self):
        s1 = Span(name="a", trace_id="t")
        s2 = Span(name="a", trace_id="t")
        assert s1.span_id != s2.span_id

    def test_duration_none_before_finish(self):
        s = Span(name="a", trace_id="t")
        assert s.duration is None

    def test_duration_after_finish(self):
        s = Span(name="a", trace_id="t")
        time.sleep(0.01)
        s.finish()
        assert s.duration is not None
        assert s.duration >= 0

    def test_finish_idempotent(self):
        s = Span(name="a", trace_id="t")
        s.finish()
        first = s.end_time
        s.finish()
        assert s.end_time == first

    def test_set_stores_attribute(self):
        s = Span(name="a", trace_id="t")
        s.set("key", 42)
        assert s.attributes["key"] == 42

    def test_to_dict_contains_name(self):
        s = Span(name="cmd", trace_id="t")
        s.finish()
        d = s.to_dict()
        assert d["name"] == "cmd"

    def test_to_dict_contains_duration(self):
        s = Span(name="cmd", trace_id="t")
        s.finish()
        assert "duration" in s.to_dict()


class TestTracer:
    def test_trace_id_is_hex(self):
        t = Tracer()
        int(t.trace_id, 16)

    def test_custom_trace_id(self):
        t = Tracer(trace_id="abc123")
        assert t.trace_id == "abc123"

    def test_start_span_adds_to_spans(self):
        t = Tracer()
        t.start_span("x")
        assert len(t.spans) == 1

    def test_spans_returns_copy(self):
        t = Tracer()
        spans = t.spans
        t.start_span("y")
        assert len(spans) == 0

    def test_finished_spans_excludes_open(self):
        t = Tracer()
        t.start_span("open")
        s = t.start_span("closed")
        s.finish()
        assert len(t.finished_spans()) == 1
        assert t.finished_spans()[0].name == "closed"

    def test_reset_clears_spans(self):
        t = Tracer()
        t.start_span("a")
        t.reset()
        assert t.spans == []

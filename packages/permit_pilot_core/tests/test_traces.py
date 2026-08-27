"""TraceRecorder parent/child spans and Langfuse removal."""

from __future__ import annotations

import unittest

from permit_pilot_core.observability.traces import TraceRecorder, TraceSpan


class _MemoryStore:
    def __init__(self) -> None:
        self.spans: list[TraceSpan] = []

    def append_trace_span(self, span: TraceSpan) -> None:
        self.spans.append(span)


class TraceRecorderTest(unittest.TestCase):
    def test_nested_spans_set_parent_id(self) -> None:
        store = _MemoryStore()
        trace = TraceRecorder(store, "case-1")
        with trace.span("distribution.run", actor="system", detail="root"):
            with trace.span("department.zoning", actor="zoning", detail="child"):
                pass

        self.assertEqual(len(store.spans), 2)
        root = next(span for span in store.spans if span.name == "distribution.run")
        child = next(span for span in store.spans if span.name == "department.zoning")
        self.assertIsNone(root.parent_id)
        self.assertEqual(child.parent_id, root.id)

    def test_langfuse_export_removed(self) -> None:
        recorder = TraceRecorder(_MemoryStore(), "case-1")
        self.assertFalse(hasattr(recorder, "_export_langfuse"))

    def test_error_span_status(self) -> None:
        store = _MemoryStore()
        trace = TraceRecorder(store, "case-1")
        with self.assertRaises(RuntimeError):
            with trace.span("runtime.orchestrator", actor="system"):
                raise RuntimeError("boom")
        self.assertEqual(store.spans[-1].status, "error")
        self.assertIn("boom", store.spans[-1].detail)


if __name__ == "__main__":
    unittest.main()

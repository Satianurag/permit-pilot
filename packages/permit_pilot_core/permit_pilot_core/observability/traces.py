from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Iterator

from pydantic import BaseModel, Field


class TraceSpan(BaseModel):
    id: str
    case_id: str
    name: str
    actor: str
    status: str = "ok"
    detail: str = ""
    parent_id: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    duration_ms: int | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(UTC)


class TraceRecorder:
    """Spans mirrored to Firestore for Audit UI; OTel spans export to Cloud Trace on Cloud Run."""

    def __init__(self, store, case_id: str) -> None:
        self._store = store
        self._case_id = case_id
        self._parent_stack: list[str] = []
        try:
            from opentelemetry import trace

            self._otel = trace.get_tracer("permit-pilot")
        except ImportError:
            self._otel = None

    def record(
        self,
        name: str,
        actor: str,
        detail: str,
        *,
        status: str = "ok",
        parent_id: str | None = None,
        span_id: str | None = None,
        attributes: dict[str, str] | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        duration_ms: int | None = None,
    ) -> TraceSpan:
        start = started_at or _now()
        end = ended_at or _now()
        span = TraceSpan(
            id=span_id or str(uuid.uuid4()),
            case_id=self._case_id,
            name=name,
            actor=actor,
            status=status,
            detail=detail,
            parent_id=parent_id,
            started_at=start,
            ended_at=end,
            duration_ms=duration_ms if duration_ms is not None else int((end - start).total_seconds() * 1000),
            attributes=attributes or {},
        )
        self._store.append_trace_span(span)
        return span

    @contextmanager
    def span(self, name: str, actor: str, detail: str = "", **attrs: str) -> Iterator[None]:
        parent_id = self._parent_stack[-1] if self._parent_stack else None
        span_id = str(uuid.uuid4())
        self._parent_stack.append(span_id)
        start = _now()
        t0 = time.perf_counter()
        status = "ok"
        final_detail = detail
        try:
            if self._otel:
                with self._otel.start_as_current_span(name) as otel_span:
                    otel_span.set_attribute("case_id", self._case_id)
                    otel_span.set_attribute("actor", actor)
                    otel_span.set_attribute("span_id", span_id)
                    if parent_id:
                        otel_span.set_attribute("parent_span_id", parent_id)
                    for key, value in attrs.items():
                        otel_span.set_attribute(key, value)
                    yield
            else:
                yield
        except Exception as exc:
            status = "error"
            final_detail = detail or str(exc)
            raise
        finally:
            self._parent_stack.pop()
            end = _now()
            ms = int((time.perf_counter() - t0) * 1000)
            self.record(
                name,
                actor,
                final_detail,
                status=status,
                parent_id=parent_id,
                span_id=span_id,
                started_at=start,
                ended_at=end,
                duration_ms=ms,
                attributes=attrs,
            )

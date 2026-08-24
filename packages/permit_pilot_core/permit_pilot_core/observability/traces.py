from __future__ import annotations

import os
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
    """Spans mirrored to Firestore for Audit UI; OTel → Cloud Trace; optional Langfuse."""

    def __init__(self, store, case_id: str) -> None:
        self._store = store
        self._case_id = case_id
        try:
            from opentelemetry import trace

            self._otel = trace.get_tracer("permit-pilot")
        except Exception:
            self._otel = None

    def record(
        self,
        name: str,
        actor: str,
        detail: str,
        *,
        status: str = "ok",
        parent_id: str | None = None,
        attributes: dict[str, str] | None = None,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        duration_ms: int | None = None,
    ) -> TraceSpan:
        start = started_at or _now()
        end = ended_at or _now()
        span = TraceSpan(
            id=str(uuid.uuid4()),
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
        self._export_langfuse(span)
        return span

    def _export_langfuse(self, span: TraceSpan) -> None:
        host = os.environ.get("LANGFUSE_HOST")
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
        if not (host and public_key and secret_key):
            return
        try:
            import httpx

            httpx.post(
                f"{host.rstrip('/')}/api/public/ingestion",
                auth=(public_key, secret_key),
                json={
                    "batch": [
                        {
                            "type": "trace-create",
                            "body": {
                                "id": span.id,
                                "name": span.name,
                                "metadata": {"case_id": span.case_id, **span.attributes},
                            },
                        },
                        {
                            "type": "span-create",
                            "body": {
                                "id": span.id,
                                "traceId": span.id,
                                "name": span.name,
                                "startTime": span.started_at.isoformat(),
                                "endTime": (span.ended_at or span.started_at).isoformat(),
                                "metadata": {"actor": span.actor, "detail": span.detail},
                            },
                        },
                    ]
                },
                timeout=5.0,
            )
        except Exception:
            pass

    @contextmanager
    def span(self, name: str, actor: str, detail: str = "", **attrs: str) -> Iterator[None]:
        start = _now()
        t0 = time.perf_counter()
        status = "ok"
        final_detail = detail
        try:
            if self._otel:
                with self._otel.start_as_current_span(name) as otel_span:
                    otel_span.set_attribute("case_id", self._case_id)
                    otel_span.set_attribute("actor", actor)
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
            end = _now()
            ms = int((time.perf_counter() - t0) * 1000)
            self.record(
                name,
                actor,
                final_detail,
                status=status,
                started_at=start,
                ended_at=end,
                duration_ms=ms,
                attributes=attrs,
            )

from __future__ import annotations

import os

_initialized = False


def setup_telemetry() -> None:
    """Configure OpenTelemetry export to Google Cloud Trace (GCP managed)."""
    global _initialized
    if _initialized or not os.environ.get("K_SERVICE"):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        resource = Resource.create(
            {
                "service.name": "permit-pilot",
                "service.namespace": project,
            }
        )
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id=project)))
        trace.set_tracer_provider(provider)
        _initialized = True
    except Exception:
        pass

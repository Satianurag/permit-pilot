from permit_pilot_core.settings import get_settings

_initialized = False


def setup_telemetry() -> None:
    """Configure OpenTelemetry export to Google Cloud Trace (GCP managed)."""
    global _initialized
    settings = get_settings()
    if _initialized or not settings.running_on_cloud_run:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        project = settings.project_id
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

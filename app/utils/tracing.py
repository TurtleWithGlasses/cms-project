"""OpenTelemetry distributed tracing setup.

Tracing is feature-flagged: it only activates when ``OTEL_EXPORTER_ENDPOINT``
is set in the environment.  When the endpoint is absent the function is a
no-op so the application starts normally in development without any OTel
packages being exercised.

Usage (in main.py, after creating the FastAPI ``app`` instance)::

    from app.utils.tracing import setup_tracing
    setup_tracing(app)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def setup_tracing(app=None) -> None:  # type: ignore[type-arg]
    """Configure the OpenTelemetry SDK and instrument FastAPI + SQLAlchemy.

    When ``settings.otel_exporter_endpoint`` is ``None`` (the default) this
    function logs a debug message and returns immediately.  No OTel packages
    are imported in that path so the application has zero OTel overhead.

    Args:
        app: The FastAPI application instance.  Required for FastAPI
            auto-instrumentation; pass ``None`` to skip it (e.g. in tests).
    """
    from app.config import settings  # local import to avoid circular deps

    if not settings.otel_exporter_endpoint:
        logger.debug("OpenTelemetry disabled: OTEL_EXPORTER_ENDPOINT not configured")
        return

    # Lazy imports — only executed when tracing is enabled.
    from opentelemetry import trace  # noqa: PLC0415
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor  # noqa: PLC0415
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # noqa: PLC0415
    from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415

    resource = Resource.create({SERVICE_NAME: settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument SQLAlchemy (works engine-globally without a reference).
    SQLAlchemyInstrumentor().instrument()

    # Instrument FastAPI when an app instance is provided.
    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: PLC0415

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="/health,/ready,/metrics,/favicon.ico",
        )

    logger.info(
        "OpenTelemetry tracing enabled → service=%s endpoint=%s",
        settings.otel_service_name,
        settings.otel_exporter_endpoint,
    )

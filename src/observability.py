"""Observability.

Phoenix reads OpenTelemetry over OTLP. PydanticAI has the instrumentation
built in, so the work here is setting up the exporter and wrapping the model.

Everything is optional. If Phoenix is not running, or the exporter cannot
reach it, the app carries on without traces. A lab that breaks when the
observability stack is down is not a lab, it is a demo.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_configured = False


def setup_tracing(
    endpoint: str | None = None,
    enabled: bool | None = None,
    service_name: str = "parallax.observer",
) -> bool:
    """Point the OpenTelemetry exporter at Phoenix.

    Returns whether tracing is on.
    """
    global _configured

    if enabled is None:
        enabled = os.environ.get("PHOENIX_ENABLED", "false").lower() in {
            "1",
            "true",
            "yes",
        }
    if not enabled:
        logger.info("tracing is off")
        return False

    if _configured:
        return True

    endpoint = endpoint or os.environ.get(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        logger.warning("the otel exporter is not installed: %s", exc)
        return False

    try:
        provider = TracerProvider(
            resource=Resource.create({"service.name": service_name})
        )
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
        )
        trace.set_tracer_provider(provider)
        logger.info("tracing is on, sending to %s", endpoint)
    except Exception as exc:
        logger.warning("could not set up tracing: %s", exc)
        return False

    _configured = True
    return True


def instrument_model(model: object) -> object:
    """Wrap a model so its calls are traced."""
    try:
        from pydantic_ai.models.instrumented import InstrumentedModel

        return InstrumentedModel(model)
    except Exception as exc:
        logger.warning("could not instrument the model: %s", exc)
        return model

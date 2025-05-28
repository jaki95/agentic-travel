import os
import base64
import logging

from dotenv import load_dotenv
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from openinference.instrumentation.agno import AgnoInstrumentor

logger = logging.getLogger(__name__)


def setup_langfuse():
    """Set up Langfuse environment variables for OpenTelemetry export."""
    load_dotenv()

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
    host = os.environ.get("LANGFUSE_HOST")

    if not all([public_key, secret_key, host]):
        logger.warning(
            "Langfuse environment variables not fully configured. Tracing will be disabled."
        )
        return False

    LANGFUSE_AUTH = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()

    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = host + "/api/public/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {LANGFUSE_AUTH}"

    logger.info("Langfuse environment variables configured successfully")
    return True


def setup_tracing():
    """Set up OpenTelemetry tracing with Langfuse integration."""
    try:
        if not setup_langfuse():
            logger.warning(
                "Skipping tracing setup due to missing Langfuse configuration"
            )
            return False

        # Configure the tracer provider
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
        trace_api.set_tracer_provider(tracer_provider=tracer_provider)

        # Start instrumenting Agno
        AgnoInstrumentor().instrument()

        logger.info(
            "OpenTelemetry tracing with Langfuse integration set up successfully"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to set up tracing: {e}")
        return False


def get_tracer(name: str = __name__):
    """Get a tracer instance for manual instrumentation."""
    return trace_api.get_tracer(name)

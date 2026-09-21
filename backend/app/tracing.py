import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.sqlalchemy import (
    SQLAlchemyInstrumentor,
)

from app.database import engine


def configure_tracing(app: FastAPI) -> None:
    service_name = os.getenv(
        "OTEL_SERVICE_NAME",
        "data-quality-backend",
    )

    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://otel-collector:4317",
    )

    resource = Resource.create(
        {
            "service.name": service_name,
        }
    )

    provider = TracerProvider(
        resource=resource,
    )

    exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,
    )

    provider.add_span_processor(
        BatchSpanProcessor(exporter)
    )

    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
    )

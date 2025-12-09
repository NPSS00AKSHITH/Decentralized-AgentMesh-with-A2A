from functools import wraps
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import os

class TelemetryManager:
    """
    Manages OpenTelemetry tracing and metrics.
    """
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.resource = Resource.create({"service.name": service_name})
        self.tracer = None

    def init_tracing(self):
        provider = TracerProvider(resource=self.resource)
        
        # Check if we are in a docker-compose environment with Jaeger
        otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://jaeger:4317")
        
        if os.getenv("ENABLE_JAEGER", "false").lower() == "true":
            # Production/Docker: Send to Jaeger
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        else:
            # Local Dev: Print to Console
            exporter = ConsoleSpanExporter()
            
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        
        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(self.service_name)
        return self.tracer

    def trace_context_decorator(self, span_name: str = None):
        """Decorator to wrap a function in an OpenTelemetry span."""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Use the tracer if initialized, otherwise no-op
                if not self.tracer:
                    return await func(*args, **kwargs)
                
                # Use function name as default span name
                name = span_name or func.__name__
                
                # Extract correlation_id if present in args/kwargs
                cid = kwargs.get("correlation_id", "UNKNOWN")
                
                with self.tracer.start_as_current_span(name) as span:
                    span.set_attribute("correlation_id", cid)
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        span.record_exception(e)
                        raise
            return wrapper
        return decorator

def get_telemetry(service_name: str) -> TelemetryManager:
    return TelemetryManager(service_name)
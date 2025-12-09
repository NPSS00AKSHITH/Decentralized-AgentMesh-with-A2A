import structlog
import logging
import os
import contextvars

# Context variable to store the correlation ID for the current request/task
correlation_id_var = contextvars.ContextVar('correlation_id', default='SYSTEM')

def add_correlation_id(_, __, event_dict: dict) -> dict:
    """Injects the current correlation ID into the log context."""
    event_dict["correlation_id"] = correlation_id_var.get()
    return event_dict

def setup_logging(service_name: str) -> structlog.BoundLogger:
    """
    Configures JSON structured logging with correlation ID tracking.
    """
    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        add_correlation_id,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        # The wrapper_class is now configured separately below to allow for dynamic level changes
        cache_logger_on_first_use=True,
    )

    # Bridge standard python logging to structlog (for libs like httpx/uvicorn)
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG,
        handlers=[logging.StreamHandler()]
    )

    logger = structlog.get_logger(service_name)
    # Force structlog to print everything
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
    )
    logger.info("Logging initialized", service=service_name)
    return logger
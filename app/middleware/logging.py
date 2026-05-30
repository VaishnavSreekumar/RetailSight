import json
import logging
import sys
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

from app.config import settings

# Global logger instance
logger = structlog.get_logger()


def setup_logging() -> None:
    """Configures structured logging for the application.

    Utilizes JSON logs for non-development environments, and console
    rendering for development.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.APP_ENV == "development":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [renderer],
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.LOG_LEVEL.upper())
        ),
        cache_logger_on_first_use=True,
    )

    # Redirect standard logging to stdout using our formatter
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.LOG_LEVEL.upper()),
    )


async def set_body(request: Request, body: bytes) -> None:
    """Replaces the request receive channel stream to allow body recaching."""
    async def receive() -> Message:
        return {"type": "http.request", "body": body, "more_body": False}
    request._receive = receive


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware responsible for logging requests and responses.

    Enforces trace IDs across all transactions and collects path metrics.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = (
            request.headers.get("X-Trace-ID")
            or request.headers.get("X-Correlation-ID")
            or str(uuid.uuid4())
        )
        
        # Safe extraction of batch event count without exhausting downstream request streams
        event_count = None
        if request.method == "POST" and "/events/ingest" in request.url.path:
            try:
                body_bytes = await request.body()
                await set_body(request, body_bytes)
                body_json = json.loads(body_bytes)
                if isinstance(body_json, dict) and "events" in body_json:
                    event_count = len(body_json["events"])
            except Exception:
                pass

        # Reset and bind request context parameters
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            endpoint=request.url.path,
            method=request.method,
            client_host=request.client.host if request.client else None,
        )
        if event_count is not None:
            structlog.contextvars.bind_contextvars(event_count=event_count)

        start_time = time.perf_counter()
        
        try:
            response: Response = await call_next(request)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            # Inject trace ID header in response
            response.headers["X-Trace-ID"] = trace_id
            
            logger.info(
                "Request processed successfully",
                status_code=response.status_code,
                latency_ms=latency_ms,
            )
            return response
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "Request failed with unhandled exception",
                status_code=500,
                latency_ms=latency_ms,
                error_message=str(exc),
            )
            raise exc

from contextvars import ContextVar
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import traceback
from uuid import UUID, uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send


request_id: ContextVar[str] = ContextVar("request_id", default="-")
LOG_DIRECTORY = Path(__file__).resolve().parents[2] / "logs"


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


class SafeFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        cached_exception = record.exc_text
        record.exc_text = None
        try:
            return super().format(record)
        finally:
            record.exc_text = cached_exception

    def formatException(self, exc_info) -> str:
        # Exception strings (including SQL parameters) can contain credentials.
        frames = traceback.extract_tb(exc_info[2])
        locations = "\n".join(
            f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}'
            for frame in frames
        )
        return f"{locations}\n{exc_info[0].__name__}"


def configure_logging() -> None:
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    formatter = SafeFormatter(
        "%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s %(message)s"
    )
    application = logging.getLogger()
    application.setLevel(logging.INFO)
    audit = logging.getLogger("shopmind.audit")
    audit.setLevel(logging.INFO)
    audit.propagate = False
    for logger, filename in (
        (application, "shopmind.log"),
        (audit, "audit.log"),
    ):
        if any(
            isinstance(handler, RotatingFileHandler)
            and handler.baseFilename == str(LOG_DIRECTORY / filename)
            for handler in logger.handlers
        ):
            continue
        handler = RotatingFileHandler(
            LOG_DIRECTORY / filename,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        handler.addFilter(CorrelationFilter())
        logger.addHandler(handler)
    # Access logs include raw URLs/query strings; use the sanitized event below.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        correlation_id = str(uuid4())
        for name, value in scope.get("headers", []):
            if name.lower() == b"x-request-id":
                try:
                    correlation_id = str(UUID(value.decode("ascii")))
                except (ValueError, UnicodeDecodeError):
                    pass  # Untrusted identifiers are replaced, never logged.
                break
        token = request_id.set(correlation_id)
        scope.setdefault("state", {})["request_id"] = correlation_id
        response_status = 500

        async def send_response(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", correlation_id.encode("ascii")),
                ]
            await send(message)

        logger = logging.getLogger("shopmind.requests")
        try:
            await self.app(scope, receive, send_response)
        except Exception:
            logger.exception("request_failed")
            raise
        finally:
            route = scope.get("route")
            logger.info(
                "request_completed method=%s route=%s status=%s",
                scope["method"],
                getattr(route, "path", "<unmatched>"),
                response_status,
            )
            request_id.reset(token)

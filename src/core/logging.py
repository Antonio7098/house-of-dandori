import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, os.environ.get("LOG_LEVEL", "INFO")))

    return logger


class LogContext:
    def __init__(self, logger: logging.Logger, **extra_fields):
        self.logger = logger
        self.extra_fields = extra_fields
        self.old_factory = None

    def __enter__(self):
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            record.extra_fields = self.extra_fields
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)
        return False


class RequestLogger:
    def __init__(self, logger_name: str = "api"):
        self.logger = get_logger(logger_name)

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **extra,
    ):
        self.logger.info(
            f"{method} {path} {status_code}",
            extra={
                "request_id": request_id or str(uuid4()),
                "user_id": user_id,
                "http": {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
                **extra,
            },
        )

    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        request_id: Optional[str] = None,
    ):
        self.logger.error(
            str(error),
            extra={
                "request_id": request_id or str(uuid4()),
                "error": {
                    "type": type(error).__name__,
                    "message": str(error),
                    "context": context,
                },
            },
            exc_info=True,
        )


api_logger = RequestLogger("api")

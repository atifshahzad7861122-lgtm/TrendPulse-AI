"""Structured logging system with JSON formatting, contextual metadata, and secret masking."""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Comprehensive regular expressions to mask credentials, tokens, cookies, and secrets
SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key|secret|token|password|auth|authorization|cookie|session)=([^&\s;\"']+)", re.IGNORECASE),
    re.compile(r"('?(?:api[_-]?key|secret|token|password|auth|authorization|cookie|session)'?\s*[:=]\s*['\"])([^'\"]+)(['\"])", re.IGNORECASE),
    re.compile(r"(Bearer\s+)([a-zA-Z0-9_\-\.]+)", re.IGNORECASE),
]


def mask_secrets(text: str) -> str:
    """Mask credentials and sensitive strings from log messages."""
    if not text:
        return text
    masked = text
    for pattern in SECRET_PATTERNS:
        masked = pattern.sub(r"\1=***REDACTED***", masked)
    return masked


class StructuredJsonFormatter(logging.Formatter):
    """JSON formatter emitting structured log events with standard scraper fields."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": mask_secrets(record.getMessage()),
        }

        # Contextual scraper fields attached via 'extra' dictionary
        context_keys = [
            "crawl_id",
            "product_id",
            "request_id",
            "event",
            "duration_ms",
            "status",
            "error",
            "url",
            "source",
            "parser",
            "retry_count",
            "challenge_type",
            "host",
        ]
        for key in context_keys:
            if hasattr(record, key):
                val = getattr(record, key)
                if isinstance(val, str):
                    val = mask_secrets(val)
                log_entry[key] = val

        if record.exc_info:
            log_entry["exception"] = mask_secrets(self.formatException(record.exc_info))

        return json.dumps(log_entry)


def setup_logger(
    name: str = "trendpulse-scraper",
    log_level: str = "INFO",
    json_format: bool = True,
) -> logging.Logger:
    """Configure and return a standardized structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Avoid duplicate handlers if setup_logger is called repeatedly
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if json_format:
            handler.setFormatter(StructuredJsonFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
                )
            )
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# Default application logger instance
logger = setup_logger()
get_logger = setup_logger

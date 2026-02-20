"""API call logging for the F1 dashboard data and service layers."""

from __future__ import annotations

import functools
import logging
import os
import threading
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "api_calls.log")

_logger: logging.Logger | None = None
_logger_lock = threading.Lock()


def _get_logger() -> logging.Logger:
    """Return the file logger, creating log dir and handler on first use."""
    global _logger
    if _logger is not None:
        return _logger

    with _logger_lock:
        if _logger is not None:
            return _logger

        os.makedirs(_LOG_DIR, exist_ok=True)

        _logger = logging.getLogger("f1_dashboard.api")
        _logger.setLevel(logging.DEBUG)
        _logger.propagate = False

        if not _logger.handlers:
            handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
            handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"),
            )
            _logger.addHandler(handler)

    return _logger


def log_api_call(fn: F) -> F:
    """Decorator that logs data-layer method calls to the API log file."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = _get_logger()
        # Build a readable argument summary (skip 'self')
        arg_parts = [repr(a) for a in args[1:]]
        arg_parts += [f"{k}={v!r}" for k, v in kwargs.items()]
        arg_str = ", ".join(arg_parts)
        logger.info("CALL: %s(%s)", fn.__qualname__, arg_str)

        start = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            elapsed = time.monotonic() - start
            count = len(result) if isinstance(result, list) else 1
            logger.info(
                "OK: %s(%s) -> %d items (%.3fs)",
                fn.__qualname__, arg_str, count, elapsed,
            )
            return result
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "FAIL: %s(%s) -> %s: %s (%.3fs)",
                fn.__qualname__, arg_str, type(exc).__name__, exc, elapsed,
            )
            raise

    return wrapper  # type: ignore[return-value]


def log_service_call(fn: F) -> F:
    """Decorator that logs service-layer method calls to the API log file."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = _get_logger()
        arg_parts = [repr(a) for a in args[1:]]
        arg_parts += [f"{k}={v!r}" for k, v in kwargs.items()]
        arg_str = ", ".join(arg_parts)
        logger.info("SERVICE CALL: %s(%s)", fn.__qualname__, arg_str)

        start = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            elapsed = time.monotonic() - start
            logger.info(
                "SERVICE OK: %s -> %.3fs", fn.__qualname__, elapsed,
            )
            return result
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "SERVICE FAIL: %s -> %s: %s (%.3fs)",
                fn.__qualname__, type(exc).__name__, exc, elapsed,
            )
            raise

    return wrapper  # type: ignore[return-value]

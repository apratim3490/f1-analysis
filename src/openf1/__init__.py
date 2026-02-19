"""OpenF1 — Typed Python client for the OpenF1 API."""

from openf1._filters import Filter
from openf1.client import AsyncOpenF1Client, OpenF1Client
from openf1.exceptions import (
    OpenF1APIError,
    OpenF1ConnectionError,
    OpenF1Error,
    OpenF1TimeoutError,
    OpenF1ValidationError,
)

__all__ = [
    "AsyncOpenF1Client",
    "Filter",
    "OpenF1APIError",
    "OpenF1Client",
    "OpenF1ConnectionError",
    "OpenF1Error",
    "OpenF1TimeoutError",
    "OpenF1ValidationError",
]

__version__ = "0.1.0"

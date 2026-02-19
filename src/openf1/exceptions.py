"""Custom exceptions for the OpenF1 client."""

from __future__ import annotations


class OpenF1Error(Exception):
    """Base exception for all OpenF1 client errors."""


class OpenF1ConnectionError(OpenF1Error):
    """Raised when the client cannot connect to the API."""


class OpenF1TimeoutError(OpenF1Error):
    """Raised when a request to the API times out."""


class OpenF1APIError(OpenF1Error):
    """Raised when the API returns an error response (4xx/5xx)."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")


class OpenF1ValidationError(OpenF1Error):
    """Raised when API response data fails model validation."""

"""Low-level HTTP transport layer wrapping httpx."""

from __future__ import annotations

from typing import Any

import httpx

from openf1.exceptions import (
    OpenF1APIError,
    OpenF1ConnectionError,
    OpenF1TimeoutError,
)

DEFAULT_BASE_URL = "https://api.openf1.org/v1"
DEFAULT_TIMEOUT = 30.0


def _handle_response(response: httpx.Response) -> list[dict[str, Any]]:
    """Validate response status and return parsed JSON."""
    if response.status_code >= 400:
        raise OpenF1APIError(
            status_code=response.status_code,
            message=response.text,
        )
    return response.json()  # type: ignore[no-any-return]


class SyncTransport:
    """Synchronous HTTP transport using httpx.Client."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    def get(self, endpoint: str, params: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Perform a GET request and return parsed JSON."""
        try:
            response = self._client.get(endpoint, params=params)
        except httpx.ConnectError as exc:
            raise OpenF1ConnectionError(str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise OpenF1TimeoutError(str(exc)) from exc
        return _handle_response(response)

    def close(self) -> None:
        self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport using httpx.AsyncClient."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    async def get(self, endpoint: str, params: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """Perform an async GET request and return parsed JSON."""
        try:
            response = await self._client.get(endpoint, params=params)
        except httpx.ConnectError as exc:
            raise OpenF1ConnectionError(str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise OpenF1TimeoutError(str(exc)) from exc
        return _handle_response(response)

    async def close(self) -> None:
        await self._client.aclose()
